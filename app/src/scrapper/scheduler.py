import asyncio
import logging

from src.scrapper.clients.bot import BotClient, BotClientError
from src.scrapper.repository.storage import InMemoryStorage
from src.scrapper.telegram_scrapper import TelegramChannelScrapper

__all__ = ("Scheduler",)

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        storage: InMemoryStorage,
        bot_client: BotClient,
        tg_scrapper: TelegramChannelScrapper,
        interval_seconds: int = 10,
    ) -> None:
        self._storage = storage
        self._bot_client = bot_client
        self._tg_scrapper = tg_scrapper
        self._interval = interval_seconds
        self._update_counter: int = 0
        self._last_message_ids: dict[str, int] = {}

    async def run(self) -> None:
        logger.info("Scheduler started", extra={"interval": self._interval})
        while True:
            await asyncio.sleep(self._interval)
            await self._check_and_notify()

    async def _check_and_notify(self) -> None:
        tracked = self._storage.get_all_tracked_links()
        for url, chat_ids in tracked.items():
            await self._process_url(url, chat_ids)

    async def _process_url(self, url: str, chat_ids: list[int]) -> None:
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
        logger.info(
            "New content detected",
            extra={"url": url, "new_posts": len(new_messages)},
        )
        await self._notify(url, chat_ids)

    async def _initialize_baseline(self, url: str) -> None:
        messages = await self._tg_scrapper.get_new_messages(url, min_id=0)
        baseline = max((m.id for m in messages), default=0)
        self._last_message_ids[url] = baseline
        logger.info("Baseline set", extra={"url": url, "baseline_id": baseline})

    async def _notify(self, url: str, chat_ids: list[int]) -> None:
        try:
            await self._bot_client.send_update(
                update_id=self._update_counter,
                url=url,
                description="Обнаружено новое обновление.",
                tg_chat_ids=chat_ids,
            )
            logger.info("Notification sent", extra={"url": url, "recipients": len(chat_ids)})
        except BotClientError as exc:
            logger.exception(
                "Failed to notify bot",
                extra={"url": url, "error": str(exc)},
            )
