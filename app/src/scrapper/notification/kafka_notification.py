import json

from src.scrapper.kafka.producer import KafkaProducerClient
from src.scrapper.notification.abstract import AbstractNotificationService, NotificationError

__all__ = ("KafkaNotificationService",)


class KafkaNotificationService(AbstractNotificationService):
    def __init__(self, producer: KafkaProducerClient, topic: str) -> None:
        self._producer = producer
        self._topic = topic

    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        tg_chat_ids: list[int],
    ) -> None:
        payload = {
            "id": update_id,
            "url": url,
            "description": description,
            "tgChatIds": tg_chat_ids,
        }
        try:
            await self._producer.send(self._topic, json.dumps(payload).encode())
        except Exception as exc:
            raise NotificationError(str(exc)) from exc
