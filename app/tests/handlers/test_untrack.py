from unittest.mock import AsyncMock

import pytest

from src.clients.scrapper import LinkResponse, ScrapperClientError
from src.handlers.untrack import make_untrack_handler


@pytest.fixture
def mock_event() -> AsyncMock:
    event = AsyncMock()
    event.chat_id = 100500
    event.respond = AsyncMock()
    return event


@pytest.fixture
def scrapper() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_untrack_happy_path(mock_event: AsyncMock, scrapper: AsyncMock) -> None:
    mock_event.raw_text = "/untrack https://t.me/ch"
    scrapper.remove_link = AsyncMock(
        return_value=LinkResponse(id=1, url="https://t.me/ch", tags=[], filters=[]),
    )
    handler = make_untrack_handler(scrapper)

    with pytest.raises(Exception):  # noqa: B017, PT011
        await handler(mock_event)

    scrapper.remove_link.assert_called_once_with(100500, "https://t.me/ch")
    response_text: str = mock_event.respond.call_args[0][0]
    assert "удалена" in response_text


@pytest.mark.asyncio
async def test_untrack_no_url(mock_event: AsyncMock, scrapper: AsyncMock) -> None:
    mock_event.raw_text = "/untrack"
    handler = make_untrack_handler(scrapper)

    with pytest.raises(Exception):  # noqa: B017, PT011
        await handler(mock_event)

    scrapper.remove_link.assert_not_called()
    response_text: str = mock_event.respond.call_args[0][0]
    assert "Укажите ссылку" in response_text


@pytest.mark.asyncio
async def test_untrack_not_found(mock_event: AsyncMock, scrapper: AsyncMock) -> None:
    mock_event.raw_text = "/untrack https://t.me/ch"
    scrapper.remove_link = AsyncMock(side_effect=ScrapperClientError(404, "not found"))
    handler = make_untrack_handler(scrapper)

    with pytest.raises(Exception):  # noqa: B017, PT011
        await handler(mock_event)

    response_text: str = mock_event.respond.call_args[0][0]
    assert "не найдена" in response_text


@pytest.mark.asyncio
async def test_untrack_scrapper_error(mock_event: AsyncMock, scrapper: AsyncMock) -> None:
    mock_event.raw_text = "/untrack https://t.me/ch"
    scrapper.remove_link = AsyncMock(side_effect=ScrapperClientError(500, "server error"))
    handler = make_untrack_handler(scrapper)

    with pytest.raises(Exception):  # noqa: B017, PT011
        await handler(mock_event)

    response_text: str = mock_event.respond.call_args[0][0]
    assert "ошибка" in response_text.lower()
