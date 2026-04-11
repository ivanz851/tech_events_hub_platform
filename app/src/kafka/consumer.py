import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import ValidationError

from src.api.updates.schemas import LinkUpdate
from src.bot.delivery import BotNotificationDelivery

__all__ = ("KafkaUpdateConsumer",)

logger = logging.getLogger(__name__)

_GROUP_ID = "bot-consumer"


class KafkaUpdateConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        dlq_topic: str,
        delivery: BotNotificationDelivery,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._dlq_topic = dlq_topic
        self._delivery = delivery

    async def run(self) -> None:
        consumer: AIOKafkaConsumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=_GROUP_ID,
        )
        producer: AIOKafkaProducer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
        )
        await consumer.start()
        await producer.start()
        try:
            async for msg in consumer:
                await self._process(msg.value, producer)
        finally:
            await consumer.stop()
            await producer.stop()

    async def _process(self, value: bytes, producer: AIOKafkaProducer) -> None:
        try:
            data = json.loads(value)
            update = LinkUpdate.model_validate(data)
        except (json.JSONDecodeError, ValidationError, KeyError) as exc:
            logger.warning(
                "Invalid Kafka message, routing to DLQ",
                extra={"error": str(exc)},
            )
            await producer.send_and_wait(self._dlq_topic, value)
            return

        message = f"Новое обновление по ссылке {update.url}:\n{update.description}"
        for chat_id in update.tg_chat_ids:
            await self._delivery.deliver(chat_id, message)
