from unittest.mock import AsyncMock

import pytest

from src.clients.scrapper import LinkValidationError, ScrapperClient
from src.handlers.track import _MSG_VALIDATION_ERROR, make_track_message_handler
from src.state.track import TrackState, TrackStateStore, TrackStep


@pytest.fixture
def state_store_with_url() -> TrackStateStore:
    store = TrackStateStore()
    store.set(111222333, TrackState(step=TrackStep.WAITING_FOR_FILTERS, url="https://example.com"))
    return store


@pytest.mark.asyncio
async def test_track_shows_validation_error_on_422(
    mock_tg_event: AsyncMock,
    state_store_with_url: TrackStateStore,
) -> None:
    scrapper = AsyncMock(spec=ScrapperClient)
    scrapper.add_link.side_effect = LinkValidationError(422, "Link validation failed")

    handler = make_track_message_handler(state_store_with_url, scrapper)
    mock_tg_event.raw_text = "/skip"
    await handler(mock_tg_event)

    mock_tg_event.respond.assert_called_once_with(_MSG_VALIDATION_ERROR)


@pytest.mark.asyncio
async def test_track_validation_error_clears_state(
    mock_tg_event: AsyncMock,
    state_store_with_url: TrackStateStore,
) -> None:
    scrapper = AsyncMock(spec=ScrapperClient)
    scrapper.add_link.side_effect = LinkValidationError(422, "Link validation failed")

    handler = make_track_message_handler(state_store_with_url, scrapper)
    mock_tg_event.raw_text = "/skip"
    await handler(mock_tg_event)

    assert not state_store_with_url.has(111222333)
