import logging

from telethon import events

from src.clients.scrapper import ScrapperClient, ScrapperClientError

__all__ = ("make_list_handler",)

logger = logging.getLogger(__name__)


def make_list_handler(scrapper: ScrapperClient) -> events.NewMessage:
    async def list_handler(event: events.NewMessage.Event) -> None:
        chat_id: int = event.chat_id
        try:
            links = await scrapper.get_links(chat_id)
        except ScrapperClientError as exc:
            logger.error("Failed to get links", extra={"chat_id": chat_id, "error": str(exc)})
            await event.respond("Произошла ошибка при получении списка ссылок.")
            raise events.StopPropagation

        if not links:
            await event.respond("Вы не отслеживаете ни одного ресурса. Используйте /track для добавления.")
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
