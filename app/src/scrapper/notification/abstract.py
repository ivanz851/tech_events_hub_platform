from abc import ABC, abstractmethod

__all__ = ("AbstractNotificationService", "NotificationError")


class NotificationError(Exception):
    pass


class AbstractNotificationService(ABC):
    @abstractmethod
    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        tg_chat_ids: list[int],
    ) -> None: ...
