import asyncio
import logging
import time

from src.metrics import detect_link_type, scrapper_scrape_duration_seconds
from src.scrapper.models import EventData, TrackedLink
from src.scrapper.notification.abstract import AbstractNotificationService, NotificationError
from src.scrapper.repository.abstract import AbstractLinkRepository
from src.scrapper.telegram_scrapper import TelegramChannelScrapper

__all__ = ("Scheduler",)

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        repository: AbstractLinkRepository,
        notification: AbstractNotificationService,
        tg_scrapper: TelegramChannelScrapper,
        interval_seconds: int = 10,
        batch_size: int = 100,
        worker_count: int = 4,
    ) -> None:
        self._repository = repository
        self._notification = notification
        self._tg_scrapper = tg_scrapper
        self._interval = interval_seconds
        self._batch_size = batch_size
        self._worker_count = worker_count
        self._update_counter: int = 0
        self._last_message_ids: dict[str, int] = {}

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

        event = _extract_event_data(new_messages[0].text if new_messages else None)
        await self._repository.save_event_data(tracked.link_id, event)
        await self._notify(url, tracked.chat_ids, event)

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


def _extract_event_data(message_text: str | None) -> EventData:
    return EventData(summary=message_text)
