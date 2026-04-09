from telethon import events

__all__ = ("unknown_command_handler",)


async def unknown_command_handler(event: events.NewMessage.Event) -> None:
    text: str = event.raw_text.strip()
    if text.startswith("/"):
        await event.respond(
            "Неизвестная команда. Используйте /help для просмотра доступных команд.",
        )
