import logging
from urllib.parse import urlparse

from telethon import events

from src.clients.scrapper import LinkAlreadyTrackedError, ScrapperClient, ScrapperClientError
from src.state.track import TrackState, TrackStateStore, TrackStep

__all__ = ("make_track_command_handler", "make_track_message_handler")

logger = logging.getLogger(__name__)

_MSG_ENTER_URL = "Введите ссылку для отслеживания:"
_MSG_ENTER_FILTERS = "Настройте теги (через пробел, опционально). Чтобы пропустить, введите /skip:"
_MSG_ALREADY_TRACKED = "Этот ресурс уже отслеживается."
_MSG_INVALID_URL = "Некорректная ссылка. Введите URL, начинающийся с http:// или https://"


def _is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except ValueError:
        return False


def make_track_command_handler(state_store: TrackStateStore) -> events.NewMessage:
    async def track_command_handler(event: events.NewMessage.Event) -> None:
        chat_id: int = event.chat_id
        text: str = event.raw_text.strip()
        parts = text.split(maxsplit=1)

        if len(parts) == 2 and _is_valid_url(parts[1]):  # noqa: PLR2004
            state_store.set(chat_id, TrackState(step=TrackStep.WAITING_FOR_FILTERS, url=parts[1]))
            await event.respond(_MSG_ENTER_FILTERS)
        else:
            state_store.set(chat_id, TrackState(step=TrackStep.WAITING_FOR_URL))
            await event.respond(_MSG_ENTER_URL)

        raise events.StopPropagation

    return track_command_handler  # type: ignore[return-value]


def make_track_message_handler(
    state_store: TrackStateStore,
    scrapper: ScrapperClient,
) -> events.NewMessage:
    async def track_message_handler(event: events.NewMessage.Event) -> None:
        chat_id: int = event.chat_id
        if not state_store.has(chat_id):
            return

        state = state_store.get(chat_id)
        assert state is not None
        text: str = event.raw_text.strip()

        if state.step == TrackStep.WAITING_FOR_URL:
            await _handle_url_input(event, chat_id, text, state_store)
        elif state.step == TrackStep.WAITING_FOR_FILTERS:
            await _handle_filters_input(event, chat_id, text, state, state_store, scrapper)

    return track_message_handler  # type: ignore[return-value]


async def _handle_url_input(
    event: events.NewMessage.Event,
    chat_id: int,
    text: str,
    state_store: TrackStateStore,
) -> None:
    if not _is_valid_url(text):
        await event.respond(_MSG_INVALID_URL)
        return
    state_store.set(chat_id, TrackState(step=TrackStep.WAITING_FOR_FILTERS, url=text))
    await event.respond(_MSG_ENTER_FILTERS)


async def _handle_filters_input(
    event: events.NewMessage.Event,
    chat_id: int,
    text: str,
    state: TrackState,
    state_store: TrackStateStore,
    scrapper: ScrapperClient,
) -> None:
    tags = [] if text == "/skip" else [t.strip() for t in text.split() if t.strip()]
    state_store.clear(chat_id)
    try:
        result = await scrapper.add_link(chat_id, state.url, tags=tags, filters=[])
        tag_info = f" [теги: {', '.join(result.tags)}]" if result.tags else ""
        await event.respond(f"Ссылка добавлена: {result.url}{tag_info}")
    except LinkAlreadyTrackedError:
        await event.respond(_MSG_ALREADY_TRACKED)
    except ScrapperClientError as exc:
        logger.exception("Failed to add link", extra={"chat_id": chat_id, "error": str(exc)})
        await event.respond("Произошла ошибка при добавлении ссылки.")
