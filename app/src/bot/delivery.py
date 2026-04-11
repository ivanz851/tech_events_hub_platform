import logging

from telethon import TelegramClient

from src.cache.digest_store import DigestStore
from src.cache.notify_mode_store import NotifyModeStore

__all__ = ("BotNotificationDelivery",)

logger = logging.getLogger(__name__)


class BotNotificationDelivery:
    def __init__(
        self,
        tg_client: TelegramClient,
        notify_mode_store: NotifyModeStore,
        digest_store: DigestStore,
    ) -> None:
        self._tg_client = tg_client
        self._notify_mode_store = notify_mode_store
        self._digest_store = digest_store

    async def deliver(self, chat_id: int, message: str) -> None:
        mode = await self._notify_mode_store.get(chat_id)
        if mode == "digest":
            await self._digest_store.add(chat_id, message)
            logger.info("Queued digest message", extra={"chat_id": chat_id})
            return
        try:
            await self._tg_client.send_message(chat_id, message)
            logger.info("Sent immediate notification", extra={"chat_id": chat_id})
        except Exception as exc:
            logger.exception(
                "Failed to send notification",
                extra={"chat_id": chat_id, "error": str(exc)},
            )
