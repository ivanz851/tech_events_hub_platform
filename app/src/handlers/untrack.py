import logging

from telethon import events

from src.clients.scrapper import ScrapperClient, ScrapperClientError

__all__ = ("make_untrack_handler",)

logger = logging.getLogger(__name__)


def make_untrack_handler(scrapper: ScrapperClient) -> events.NewMessage:
    async def untrack_handler(event: events.NewMessage.Event) -> None:
        chat_id: int = event.chat_id
        text: str = event.raw_text.strip()
        parts = text.split(maxsplit=1)

        if len(parts) < 2:
            await event.respond("Укажите ссылку для удаления. Пример: /untrack https://t.me/channel")
            raise events.StopPropagation

        link = parts[1].strip()
        try:
            result = await scrapper.remove_link(chat_id, link)
            await event.respond(f"Ссылка удалена: {result.url}")
        except ScrapperClientError as exc:
            if exc.status_code == 404:
                await event.respond("Ссылка не найдена в списке отслеживаемых.")
            else:
                logger.error("Failed to remove link", extra={"chat_id": chat_id, "error": str(exc)})
                await event.respond("Произошла ошибка при удалении ссылки.")

        raise events.StopPropagation

    return untrack_handler  # type: ignore[return-value]
