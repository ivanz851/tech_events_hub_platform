from unittest.mock import AsyncMock, Mock

import pytest

from src.clients.scrapper import LinkAlreadyTrackedError, LinkResponse, ScrapperClientError
from src.handlers.track import make_track_command_handler, make_track_message_handler
from src.state.track import TrackState, TrackStateStore, TrackStep


@pytest.fixture
def mock_event() -> Mock:
    event = AsyncMock()
    event.chat_id = 100500
    event.raw_text = ""
    event.respond = AsyncMock()
    return event


@pytest.fixture
def scrapper() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def store() -> TrackStateStore:
    return TrackStateStore()


@pytest.mark.asyncio
@pytest.mark.usefixtures("scrapper")
async def test_track_command_sets_waiting_url_state(
    mock_event: Mock,
    store: TrackStateStore,
) -> None:
    mock_event.raw_text = "/track"
    handler = make_track_command_handler(store)

    with pytest.raises(Exception):  # noqa: B017, PT011
        await handler(mock_event)

    state = store.get(100500)
    assert state is not None
    assert state.step == TrackStep.WAITING_FOR_URL
    mock_event.respond.assert_called_once()


@pytest.mark.asyncio
async def test_track_command_with_url_skips_to_filters(
    mock_event: Mock,
    store: TrackStateStore,
) -> None:
    mock_event.raw_text = "/track https://t.me/somechannel"
    handler = make_track_command_handler(store)

    with pytest.raises(Exception):  # noqa: B017, PT011
        await handler(mock_event)

    state = store.get(100500)
    assert state is not None
    assert state.step == TrackStep.WAITING_FOR_FILTERS
    assert state.url == "https://t.me/somechannel"


@pytest.mark.asyncio
async def test_track_message_valid_url(
    mock_event: Mock,
    store: TrackStateStore,
    scrapper: AsyncMock,
) -> None:
    store.set(100500, TrackState(step=TrackStep.WAITING_FOR_URL))
    mock_event.raw_text = "https://t.me/testchannel"
    handler = make_track_message_handler(store, scrapper)
    await handler(mock_event)

    state = store.get(100500)
    assert state is not None
    assert state.step == TrackStep.WAITING_FOR_FILTERS
    assert state.url == "https://t.me/testchannel"


@pytest.mark.asyncio
async def test_track_message_invalid_url(
    mock_event: Mock,
    store: TrackStateStore,
    scrapper: AsyncMock,
) -> None:
    store.set(100500, TrackState(step=TrackStep.WAITING_FOR_URL))
    mock_event.raw_text = "not-a-url"
    handler = make_track_message_handler(store, scrapper)
    await handler(mock_event)

    state = store.get(100500)
    assert state is not None
    assert state.step == TrackStep.WAITING_FOR_URL
    mock_event.respond.assert_called_once()


@pytest.mark.asyncio
async def test_track_filters_saved_and_link_added(
    mock_event: Mock,
    store: TrackStateStore,
    scrapper: AsyncMock,
) -> None:
    store.set(100500, TrackState(step=TrackStep.WAITING_FOR_FILTERS, url="https://t.me/ch"))
    mock_event.raw_text = "python backend"
    scrapper.add_link = AsyncMock(
        return_value=LinkResponse(
            id=1,
            url="https://t.me/ch",
            tags=["python", "backend"],
            filters=[],
        ),
    )
    handler = make_track_message_handler(store, scrapper)
    await handler(mock_event)

    scrapper.add_link.assert_called_once_with(
        100500,
        "https://t.me/ch",
        tags=["python", "backend"],
        filters=[],
    )
    assert not store.has(100500)
    mock_event.respond.assert_called_once()


@pytest.mark.asyncio
async def test_track_filters_skip(
    mock_event: Mock,
    store: TrackStateStore,
    scrapper: AsyncMock,
) -> None:
    store.set(100500, TrackState(step=TrackStep.WAITING_FOR_FILTERS, url="https://t.me/ch"))
    mock_event.raw_text = "/skip"
    scrapper.add_link = AsyncMock(
        return_value=LinkResponse(id=1, url="https://t.me/ch", tags=[], filters=[]),
    )
    handler = make_track_message_handler(store, scrapper)
    await handler(mock_event)

    scrapper.add_link.assert_called_once_with(100500, "https://t.me/ch", tags=[], filters=[])


@pytest.mark.asyncio
async def test_track_duplicate_link(
    mock_event: Mock,
    store: TrackStateStore,
    scrapper: AsyncMock,
) -> None:
    store.set(100500, TrackState(step=TrackStep.WAITING_FOR_FILTERS, url="https://t.me/ch"))
    mock_event.raw_text = "/skip"
    scrapper.add_link = AsyncMock(side_effect=LinkAlreadyTrackedError(409, "already tracked"))
    handler = make_track_message_handler(store, scrapper)
    await handler(mock_event)

    mock_event.respond.assert_called_once()
    assert "уже отслеживается" in mock_event.respond.call_args[0][0]


@pytest.mark.asyncio
async def test_track_scrapper_error(
    mock_event: Mock,
    store: TrackStateStore,
    scrapper: AsyncMock,
) -> None:
    store.set(100500, TrackState(step=TrackStep.WAITING_FOR_FILTERS, url="https://t.me/ch"))
    mock_event.raw_text = "/skip"
    scrapper.add_link = AsyncMock(side_effect=ScrapperClientError(500, "server error"))
    handler = make_track_message_handler(store, scrapper)
    await handler(mock_event)

    mock_event.respond.assert_called_once()
    assert "ошибка" in mock_event.respond.call_args[0][0].lower()
