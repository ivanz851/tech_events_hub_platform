from aiokafka import AIOKafkaProducer

__all__ = ("KafkaProducerClient",)


class KafkaProducerClient:
    def __init__(self, bootstrap_servers: str) -> None:
        self._producer: AIOKafkaProducer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
        )

    async def start(self) -> None:
        await self._producer.start()

    async def stop(self) -> None:
        await self._producer.stop()

    async def send(self, topic: str, value: bytes) -> None:
        await self._producer.send_and_wait(topic, value)
