import logging

from telethon import events

from src.cache.list_cache import ListCache
from src.clients.scrapper import LinkResponse, ScrapperClient, ScrapperClientError

__all__ = ("make_list_handler",)

logger = logging.getLogger(__name__)


async def _fetch_links(
    scrapper: ScrapperClient,
    cache: ListCache | None,
    chat_id: int,
) -> list[LinkResponse]:
    if cache is not None:
        cached = await cache.get(chat_id)
        if cached is not None:
            return cached
    links = await scrapper.get_links(chat_id)
    if cache is not None:
        await cache.set(chat_id, links)
    return links


def make_list_handler(
    scrapper: ScrapperClient,
    cache: ListCache | None = None,
) -> events.NewMessage:
    async def list_handler(event: events.NewMessage.Event) -> None:
        chat_id: int = event.chat_id
        try:
            links = await _fetch_links(scrapper, cache, chat_id)
        except ScrapperClientError as exc:
            logger.exception(
                "Failed to get links",
                extra={"chat_id": chat_id, "error": str(exc)},
            )
            await event.respond("Произошла ошибка при получении списка ссылок.")
            raise events.StopPropagation from exc

        if not links:
            await event.respond(
                "Вы не отслеживаете ни одного ресурса. Используйте /track для добавления.",
            )
            raise events.StopPropagation

        lines = ["Отслеживаемые ресурсы:"]
        for link in links:
            line = f"• {link.url}"
            if link.tags:
                line += f" [теги: {', '.join(link.tags)}]"
            lines.append(line)

        await event.respond("\n".join(lines))
        raise events.StopPropagation

    return list_handler  # type: ignore[return-value]
