from src.scrapper.clients.bot import BotClient, BotClientError
from src.scrapper.notification.abstract import AbstractNotificationService, NotificationError

__all__ = ("HttpNotificationService",)


class HttpNotificationService(AbstractNotificationService):
    def __init__(self, bot_client: BotClient) -> None:
        self._client = bot_client

    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        tg_chat_ids: list[int],
    ) -> None:
        try:
            await self._client.send_update(
                update_id=update_id,
                url=url,
                description=description,
                tg_chat_ids=tg_chat_ids,
            )
        except BotClientError as exc:
            raise NotificationError(str(exc)) from exc
