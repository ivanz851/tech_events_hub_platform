import logging
from http import HTTPStatus

from telethon import events

from src.clients.scrapper import ScrapperClient, ScrapperClientError
from src.state.track import TrackState, TrackStateStore, TrackStep

__all__ = ("make_untrack_handler",)

logger = logging.getLogger(__name__)


def make_untrack_handler(
    scrapper: ScrapperClient,
    state_store: TrackStateStore,
) -> events.NewMessage:
    async def untrack_handler(event: events.NewMessage.Event) -> None:
        chat_id: int = event.chat_id
        text: str = event.raw_text.strip()
        parts = text.split(maxsplit=1)

        if len(parts) < 2:  # noqa: PLR2004
            state_store.set(chat_id, TrackState(step=TrackStep.WAITING_FOR_UNTRACK_URL))
            await event.respond("Введите ссылку для удаления из отслеживания:")
            raise events.StopPropagation

        await _do_untrack(event, chat_id, parts[1].strip(), scrapper, state_store)
        raise events.StopPropagation

    return untrack_handler  # type: ignore[return-value]


async def _do_untrack(
    event: events.NewMessage.Event,
    chat_id: int,
    link: str,
    scrapper: ScrapperClient,
    state_store: TrackStateStore,
) -> None:
    state_store.clear(chat_id)
    try:
        result = await scrapper.remove_link(chat_id, link)
        await event.respond(f"Ссылка удалена: {result.url}")
    except ScrapperClientError as exc:
        if exc.status_code == HTTPStatus.NOT_FOUND:
            await event.respond("Ссылка не найдена в списке отслеживаемых.")
        else:
            logger.exception("Failed to remove link", extra={"chat_id": chat_id, "error": str(exc)})
            await event.respond("Произошла ошибка при удалении ссылки.")
