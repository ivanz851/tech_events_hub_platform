from src.scrapper.notification.abstract import AbstractNotificationService

__all__ = ("FallbackNotificationService",)


class FallbackNotificationService(AbstractNotificationService):
    def __init__(
        self,
        primary: AbstractNotificationService,
        fallback: AbstractNotificationService,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        tg_chat_ids: list[int],
    ) -> None:
        from src.scrapper.notification.abstract import NotificationError

        try:
            await self._primary.send_update(update_id, url, description, tg_chat_ids)
        except NotificationError:
            await self._fallback.send_update(update_id, url, description, tg_chat_ids)
