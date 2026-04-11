import asyncio
import logging
from datetime import datetime, timedelta

from telethon import TelegramClient

from src.cache.digest_store import DigestStore

__all__ = ("DigestScheduler",)

logger = logging.getLogger(__name__)


class DigestScheduler:
    def __init__(
        self,
        digest_store: DigestStore,
        tg_client: TelegramClient,
        digest_time: str,
    ) -> None:
        self._digest_store = digest_store
        self._tg_client = tg_client
        self._digest_time = digest_time

    async def run(self) -> None:
        while True:
            await self._sleep_until_digest()
            await self._send_all_digests()

    async def _sleep_until_digest(self) -> None:
        now = datetime.now()  # noqa: DTZ005
        hour, minute = (int(p) for p in self._digest_time.split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

    async def _send_all_digests(self) -> None:
        users = await self._digest_store.get_users()
        for chat_id in users:
            await self._send_digest(chat_id)

    async def _send_digest(self, chat_id: int) -> None:
        messages = await self._digest_store.get_all(chat_id)
        await self._digest_store.clear(chat_id)
        if not messages:
            return
        digest = "Дайджест обновлений:\n\n" + "\n\n---\n\n".join(messages)
        try:
            await self._tg_client.send_message(chat_id, digest)
        except Exception as exc:
            logger.exception(
                "Failed to send digest",
                extra={"chat_id": chat_id, "error": str(exc)},
            )
