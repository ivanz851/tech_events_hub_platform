import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from src.api.updates.schemas import LinkUpdate
from src.kafka.consumer import KafkaUpdateConsumer
from tests.bot.conftest import skip_without_docker

_VALID_PAYLOAD = {
    "id": 1,
    "url": "https://t.me/testchannel",
    "description": "Тестовое событие",
    "tgChatIds": [111, 222],
}


def test_link_update_json_to_dto() -> None:
    update = LinkUpdate.model_validate(_VALID_PAYLOAD)
    assert update.id == 1
    assert update.url == "https://t.me/testchannel"
    assert update.description == "Тестовое событие"
    assert update.tg_chat_ids == [111, 222]


@pytest.mark.asyncio
async def test_process_valid_message_delivers_to_all_chats() -> None:
    delivery = AsyncMock()
    mock_producer = AsyncMock()

    consumer = KafkaUpdateConsumer(
        bootstrap_servers="localhost:9092",
        topic="updates",
        dlq_topic="updates.dlq",
        delivery=delivery,
    )

    payload = json.dumps(_VALID_PAYLOAD).encode()
    await consumer._process(payload, mock_producer)

    assert delivery.deliver.call_count == 2
    mock_producer.send_and_wait.assert_not_called()


@pytest.mark.asyncio
async def test_process_invalid_json_routes_to_dlq() -> None:
    delivery = AsyncMock()
    mock_producer = AsyncMock()

    consumer = KafkaUpdateConsumer(
        bootstrap_servers="localhost:9092",
        topic="updates",
        dlq_topic="updates.dlq",
        delivery=delivery,
    )

    invalid_bytes = b"not valid json {"
    await consumer._process(invalid_bytes, mock_producer)

    mock_producer.send_and_wait.assert_called_once_with("updates.dlq", invalid_bytes)
    delivery.deliver.assert_not_called()


@pytest.mark.asyncio
async def test_process_schema_validation_error_routes_to_dlq() -> None:
    delivery = AsyncMock()
    mock_producer = AsyncMock()

    consumer = KafkaUpdateConsumer(
        bootstrap_servers="localhost:9092",
        topic="updates",
        dlq_topic="updates.dlq",
        delivery=delivery,
    )

    bad_schema = json.dumps({"id": "not-an-int", "url": 123}).encode()
    await consumer._process(bad_schema, mock_producer)

    mock_producer.send_and_wait.assert_called_once()
    delivery.deliver.assert_not_called()


@skip_without_docker
@pytest.mark.asyncio
async def test_kafka_end_to_end_consume_and_deliver() -> None:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from testcontainers.kafka import KafkaContainer

    topic = "test.updates.e2e"
    dlq_topic = "test.updates.dlq"

    with KafkaContainer() as kafka:
        servers = kafka.get_bootstrap_server()

        producer = AIOKafkaProducer(bootstrap_servers=servers)
        await producer.start()
        payload = json.dumps(_VALID_PAYLOAD).encode()
        await producer.send_and_wait(topic, payload)
        await producer.stop()

        delivery = AsyncMock()
        dlq_producer = AIOKafkaProducer(bootstrap_servers=servers)
        await dlq_producer.start()

        consumer_client = AIOKafkaConsumer(
            topic,
            bootstrap_servers=servers,
            auto_offset_reset="earliest",
            group_id="test-group-e2e",
        )
        await consumer_client.start()

        update_consumer = KafkaUpdateConsumer(
            bootstrap_servers=servers,
            topic=topic,
            dlq_topic=dlq_topic,
            delivery=delivery,
        )

        try:
            msg = await asyncio.wait_for(consumer_client.__anext__(), timeout=10.0)
            await update_consumer._process(msg.value, dlq_producer)
        finally:
            await consumer_client.stop()
            await dlq_producer.stop()

    assert delivery.deliver.call_count == 2
