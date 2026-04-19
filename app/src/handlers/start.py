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
        raw_text: str = event.raw_text or ""
        parts = raw_text.strip().split(maxsplit=1)
        link_token: str | None = parts[1] if len(parts) > 1 else None

        if link_token:
            try:
                await scrapper.link_telegram(link_token, chat_id)
                await event.respond(
                    "✅ Ваш Telegram успешно привязан к Web-аккаунту! "
                    "Теперь вы можете настраивать подписки на сайте.",
                )
            except ScrapperClientError as exc:
                logger.exception(
                    "Failed to link telegram account",
                    extra={"chat_id": chat_id, "error": str(exc)},
                )
                await event.respond(
                    "❌ Ссылка устарела или недействительна. Сгенерируйте новую на сайте.",
                )
            raise events.StopPropagation

        try:
            await scrapper.register_chat(chat_id)
            await event.respond(
                "Добро пожаловать! Вы зарегистрированы. Используйте /help для просмотра команд.",
            )
        except ScrapperClientError as exc:
            logger.exception(
                "Failed to register chat",
                extra={"chat_id": chat_id, "error": str(exc)},
            )
            await event.respond("Произошла ошибка при регистрации. Попробуйте позже.")
        raise events.StopPropagation

    return start_handler  # type: ignore[return-value]
