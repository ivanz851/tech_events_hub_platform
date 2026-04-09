from unittest.mock import AsyncMock

import pytest

from src.handlers.unknown import unknown_command_handler


@pytest.fixture
def mock_event() -> AsyncMock:
    event = AsyncMock()
    event.chat_id = 100500
    event.respond = AsyncMock()
    return event


@pytest.mark.asyncio
async def test_unknown_command_sends_notification(mock_event: AsyncMock) -> None:
    mock_event.raw_text = "/unknown_command"
    await unknown_command_handler(mock_event)

    mock_event.respond.assert_called_once()
    response_text: str = mock_event.respond.call_args[0][0]
    assert "Неизвестная команда" in response_text
    assert "/help" in response_text


@pytest.mark.asyncio
async def test_non_command_text_ignored(mock_event: AsyncMock) -> None:
    mock_event.raw_text = "просто текст без команды"
    await unknown_command_handler(mock_event)

    mock_event.respond.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_slash_command(mock_event: AsyncMock) -> None:
    mock_event.raw_text = "/foobar"
    await unknown_command_handler(mock_event)

    mock_event.respond.assert_called_once()
