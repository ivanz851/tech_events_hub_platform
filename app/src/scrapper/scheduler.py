from __future__ import annotations
import asyncio
import hashlib
import logging
import time
from typing import TYPE_CHECKING

from src.metrics import detect_link_type, scrapper_scrape_duration_seconds
from src.scrapper.models import EventData, TrackedLink
from src.scrapper.notification.abstract import AbstractNotificationService, NotificationError
from src.scrapper.strategies.abstract import LinkValidationError

if TYPE_CHECKING:
    from src.scrapper.llm.client import LLMEventResult, YandexLLMClient
    from src.scrapper.repository.abstract import AbstractLinkRepository
    from src.scrapper.strategies.web import WebScrapperStrategy
    from src.scrapper.telegram_scrapper import TelegramChannelScrapper

__all__ = ("Scheduler",)

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        repository: AbstractLinkRepository,
        notification: AbstractNotificationService,
        tg_scrapper: TelegramChannelScrapper,
        web_strategy: WebScrapperStrategy | None = None,
        interval_seconds: int = 10,
        batch_size: int = 100,
        worker_count: int = 4,
        llm_client: YandexLLMClient | None = None,
    ) -> None:
        self._repository = repository
        self._notification = notification
        self._tg_scrapper = tg_scrapper
        self._web_strategy = web_strategy
        self._interval = interval_seconds
        self._batch_size = batch_size
        self._worker_count = worker_count
        self._llm_client = llm_client
        self._update_counter: int = 0
        self._last_message_ids: dict[str, int] = {}
        self._last_content_hashes: dict[str, str] = {}

    async def run(self) -> None:
        logger.info("Scheduler started", extra={"interval": self._interval})
        while True:
            await asyncio.sleep(self._interval)
            await self._check_and_notify()

    async def _check_and_notify(self) -> None:
        offset = 0
        while True:
            batch = await self._repository.get_tracked_links_page(offset, self._batch_size)
            if not batch:
                break
            await self._process_batch_concurrent(batch)
            offset += self._batch_size

    async def _process_batch_concurrent(self, batch: list[TrackedLink]) -> None:
        chunk_size = max(1, (len(batch) + self._worker_count - 1) // self._worker_count)
        chunks = [batch[i : i + chunk_size] for i in range(0, len(batch), chunk_size)]
        await asyncio.gather(*[self._process_chunk(chunk) for chunk in chunks])

    async def _process_chunk(self, chunk: list[TrackedLink]) -> None:
        for tracked in chunk:
            await self._process_url(tracked)

    async def _process_url(self, tracked: TrackedLink) -> None:
        url = tracked.url
        link_type = detect_link_type(url)
        start = time.monotonic()
        try:
            await self._process_url_inner(tracked)
        finally:
            scrapper_scrape_duration_seconds.labels(link_type=link_type).observe(
                time.monotonic() - start,
            )

    async def _process_url_inner(self, tracked: TrackedLink) -> None:
        if detect_link_type(tracked.url) == "telegram":
            await self._process_telegram_url(tracked)
        elif self._web_strategy is not None:
            await self._process_web_url(tracked, self._web_strategy)

    async def _process_telegram_url(self, tracked: TrackedLink) -> None:
        url = tracked.url
        if url not in self._last_message_ids:
            await self._initialize_baseline(url)
            return

        min_id = self._last_message_ids[url]
        new_messages = await self._tg_scrapper.get_new_messages(url, min_id=min_id)
        if not new_messages:
            return

        max_id = max(m.id for m in new_messages)
        if max_id <= min_id:
            return

        self._last_message_ids[url] = max_id
        self._update_counter += 1
        logger.info("New content detected", extra={"url": url, "new_posts": len(new_messages)})

        text = new_messages[0].text if new_messages else None
        event = await self._analyze_content(text, url, fallback=EventData(summary=text))
        if event is None:
            logger.info("Not an IT event, skipping notification", extra={"url": url})
            return
        await self._repository.save_event_data(tracked.link_id, event)
        await self._notify(url, tracked.chat_ids, event)

    async def _process_web_url(
        self,
        tracked: TrackedLink,
        web_strategy: WebScrapperStrategy,
    ) -> None:
        url = tracked.url
        try:
            content = await web_strategy.fetch_content(url)
        except LinkValidationError:
            logger.exception("Failed to fetch web content", extra={"url": url})
            return

        current_hash = hashlib.sha256(content.encode()).hexdigest()
        if url not in self._last_content_hashes:
            self._last_content_hashes[url] = current_hash
            logger.info("Web baseline set", extra={"url": url})
            return

        if self._last_content_hashes[url] == current_hash:
            return

        self._last_content_hashes[url] = current_hash
        self._update_counter += 1
        logger.info("Web content changed", extra={"url": url})
        fallback = EventData(summary=f"Страница обновилась: {url}")
        event = await self._analyze_content(content, url, fallback=fallback)
        if event is None:
            logger.info("Not an IT event, skipping notification", extra={"url": url})
            return
        await self._repository.save_event_data(tracked.link_id, event)
        await self._notify(url, tracked.chat_ids, event)

    async def _analyze_content(
        self,
        text: str | None,
        url: str,
        fallback: EventData,
    ) -> EventData | None:
        if self._llm_client is None or not text:
            return fallback
        result = await self._llm_client.analyze(text, url)
        if result is None or not result.is_event:
            return None
        return _llm_result_to_event_data(result)

    async def _initialize_baseline(self, url: str) -> None:
        messages = await self._tg_scrapper.get_new_messages(url, min_id=0)
        baseline = max((m.id for m in messages), default=0)
        self._last_message_ids[url] = baseline
        logger.info("Baseline set", extra={"url": url, "baseline_id": baseline})

    async def _notify(self, url: str, chat_ids: list[int], event: EventData) -> None:
        from src.scrapper.notification.formatter import format_event_notification

        description = format_event_notification(url, event)
        try:
            await self._notification.send_update(
                update_id=self._update_counter,
                url=url,
                description=description,
                tg_chat_ids=chat_ids,
            )
            logger.info("Notification sent", extra={"url": url, "recipients": len(chat_ids)})
        except NotificationError as exc:
            logger.exception("Failed to notify bot", extra={"url": url, "error": str(exc)})


def _llm_result_to_event_data(result: LLMEventResult) -> EventData:
    return EventData(
        title=result.title,
        event_date=result.event_date,
        location=result.location,
        price=result.price,
        registration_url=result.registration_url,
        format=result.format,
        event_type=result.event_type,
        summary=result.summary,
        tags=result.tags,
        organizer=result.organizer,
    )
