from unittest.mock import AsyncMock

import pytest

from src.clients.scrapper import LinkResponse, ScrapperClientError
from src.handlers.list_links import make_list_handler


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
async def test_list_empty(mock_event: AsyncMock, scrapper: AsyncMock) -> None:
    scrapper.get_links = AsyncMock(return_value=[])
    handler = make_list_handler(scrapper)

    with pytest.raises(Exception):
        await handler(mock_event)

    response_text: str = mock_event.respond.call_args[0][0]
    assert "не отслеживаете" in response_text


@pytest.mark.asyncio
async def test_list_with_links(mock_event: AsyncMock, scrapper: AsyncMock) -> None:
    scrapper.get_links = AsyncMock(
        return_value=[
            LinkResponse(id=1, url="https://t.me/ch1", tags=["python"], filters=[]),
            LinkResponse(id=2, url="https://t.me/ch2", tags=[], filters=[]),
        ],
    )
    handler = make_list_handler(scrapper)

    with pytest.raises(Exception):
        await handler(mock_event)

    response_text: str = mock_event.respond.call_args[0][0]
    assert "https://t.me/ch1" in response_text
    assert "https://t.me/ch2" in response_text
    assert "python" in response_text
    assert "Отслеживаемые ресурсы:" in response_text


@pytest.mark.asyncio
async def test_list_scrapper_error(mock_event: AsyncMock, scrapper: AsyncMock) -> None:
    scrapper.get_links = AsyncMock(side_effect=ScrapperClientError(500, "error"))
    handler = make_list_handler(scrapper)

    with pytest.raises(Exception):
        await handler(mock_event)

    response_text: str = mock_event.respond.call_args[0][0]
    assert "ошибка" in response_text.lower()
