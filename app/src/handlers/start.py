import logging

from telethon import events

from src.clients.scrapper import ScrapperClient, ScrapperClientError

__all__ = ("make_start_handler",)

logger = logging.getLogger(__name__)


def make_start_handler(
    scrapper: ScrapperClient,
) -> events.NewMessage:
    async def start_handler(event: events.NewMessage.Event) -> None:
        chat_id: int = event.chat_id
        try:
            await scrapper.register_chat(chat_id)
            await event.respond("Добро пожаловать! Вы зарегистрированы. Используйте /help для просмотра команд.")
        except ScrapperClientError as exc:
            logger.error("Failed to register chat", extra={"chat_id": chat_id, "error": str(exc)})
            await event.respond("Произошла ошибка при регистрации. Попробуйте позже.")
        raise events.StopPropagation

    return start_handler  # type: ignore[return-value]
