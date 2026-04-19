from unittest.mock import AsyncMock

import pytest

from src.clients.scrapper import LinkResponse, ScrapperClientError
from src.handlers.untrack import make_untrack_handler
from src.state.track import TrackStateStore, TrackStep


@pytest.fixture
def mock_event() -> AsyncMock:
    event = AsyncMock()
    event.chat_id = 100500
    event.respond = AsyncMock()
    return event


@pytest.fixture
def scrapper() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def state_store() -> TrackStateStore:
    return TrackStateStore()


@pytest.mark.asyncio
async def test_untrack_happy_path(
    mock_event: AsyncMock,
    scrapper: AsyncMock,
    state_store: TrackStateStore,
) -> None:
    mock_event.raw_text = "/untrack https://t.me/ch"
    scrapper.remove_link = AsyncMock(
        return_value=LinkResponse(id=1, url="https://t.me/ch"),
    )
    handler = make_untrack_handler(scrapper, state_store)

    with pytest.raises(Exception):
        await handler(mock_event)

    scrapper.remove_link.assert_called_once_with(100500, "https://t.me/ch")
    response_text: str = mock_event.respond.call_args[0][0]
    assert "удалена" in response_text


@pytest.mark.asyncio
async def test_untrack_no_url_sets_state_and_prompts(
    mock_event: AsyncMock,
    scrapper: AsyncMock,
    state_store: TrackStateStore,
) -> None:
    mock_event.raw_text = "/untrack"
    handler = make_untrack_handler(scrapper, state_store)

    with pytest.raises(Exception):
        await handler(mock_event)

    scrapper.remove_link.assert_not_called()
    assert state_store.has(100500)

    state = state_store.get(100500)
    assert state is not None
    assert state.step == TrackStep.WAITING_FOR_UNTRACK_URL

    response_text: str = mock_event.respond.call_args[0][0]
    assert "Введите ссылку" in response_text


@pytest.mark.asyncio
async def test_untrack_not_found(
    mock_event: AsyncMock,
    scrapper: AsyncMock,
    state_store: TrackStateStore,
) -> None:
    mock_event.raw_text = "/untrack https://t.me/ch"
    scrapper.remove_link = AsyncMock(side_effect=ScrapperClientError(404, "not found"))
    handler = make_untrack_handler(scrapper, state_store)

    with pytest.raises(Exception):
        await handler(mock_event)

    response_text: str = mock_event.respond.call_args[0][0]
    assert "не найдена" in response_text


@pytest.mark.asyncio
async def test_untrack_scrapper_error(
    mock_event: AsyncMock,
    scrapper: AsyncMock,
    state_store: TrackStateStore,
) -> None:
    mock_event.raw_text = "/untrack https://t.me/ch"
    scrapper.remove_link = AsyncMock(side_effect=ScrapperClientError(500, "server error"))
    handler = make_untrack_handler(scrapper, state_store)

    with pytest.raises(Exception):
        await handler(mock_event)

    response_text: str = mock_event.respond.call_args[0][0]
    assert "ошибка" in response_text.lower()


@pytest.mark.asyncio
async def test_untrack_clears_state_after_success(
    mock_event: AsyncMock,
    scrapper: AsyncMock,
    state_store: TrackStateStore,
) -> None:
    mock_event.raw_text = "/untrack https://t.me/ch"
    scrapper.remove_link = AsyncMock(
        return_value=LinkResponse(id=1, url="https://t.me/ch"),
    )
    handler = make_untrack_handler(scrapper, state_store)

    with pytest.raises(Exception):
        await handler(mock_event)

    assert not state_store.has(100500)


@pytest.mark.asyncio
async def test_untrack_clears_state_on_not_found(
    mock_event: AsyncMock,
    scrapper: AsyncMock,
    state_store: TrackStateStore,
) -> None:
    mock_event.raw_text = "/untrack https://t.me/ch"
    scrapper.remove_link = AsyncMock(side_effect=ScrapperClientError(404, "not found"))
    handler = make_untrack_handler(scrapper, state_store)

    with pytest.raises(Exception):
        await handler(mock_event)

    assert not state_store.has(100500)
