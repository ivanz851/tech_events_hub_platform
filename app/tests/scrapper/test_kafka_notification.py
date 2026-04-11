import json
from unittest.mock import AsyncMock

import pytest

from src.scrapper.notification.abstract import NotificationError
from src.scrapper.notification.kafka_notification import KafkaNotificationService


@pytest.mark.asyncio
async def test_send_update_sends_correct_json() -> None:
    mock_producer = AsyncMock()
    mock_producer.send = AsyncMock()

    service = KafkaNotificationService(producer=mock_producer, topic="test.topic")
    await service.send_update(
        update_id=42,
        url="https://t.me/ch",
        description="Тест",
        tg_chat_ids=[111, 222],
    )

    mock_producer.send.assert_called_once()
    call_args = mock_producer.send.call_args
    topic_arg = call_args[0][0]
    payload_bytes = call_args[0][1]

    assert topic_arg == "test.topic"
    payload = json.loads(payload_bytes)
    assert payload["id"] == 42
    assert payload["url"] == "https://t.me/ch"
    assert payload["description"] == "Тест"
    assert payload["tgChatIds"] == [111, 222]


@pytest.mark.asyncio
async def test_send_update_wraps_exception_as_notification_error() -> None:
    mock_producer = AsyncMock()
    mock_producer.send = AsyncMock(side_effect=RuntimeError("broker down"))

    service = KafkaNotificationService(producer=mock_producer, topic="test.topic")

    with pytest.raises(NotificationError):
        await service.send_update(
            update_id=1,
            url="https://t.me/ch",
            description="x",
            tg_chat_ids=[1],
        )


def test_kafka_payload_matches_link_update_schema() -> None:
    from src.api.updates.schemas import LinkUpdate

    raw = {
        "id": 7,
        "url": "https://t.me/channel",
        "description": "Event",
        "tgChatIds": [100, 200],
    }
    update = LinkUpdate.model_validate(raw)
    assert update.id == 7
    assert update.url == "https://t.me/channel"
    assert update.tg_chat_ids == [100, 200]
