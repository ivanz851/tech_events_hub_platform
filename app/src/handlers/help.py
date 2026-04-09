from telethon import events

__all__ = ("help_handler",)

_HELP_TEXT = (
    "Доступные команды:\n"
    "/start — регистрация\n"
    "/help — список команд\n"
    "/track — начать отслеживание ресурса\n"
    "/untrack — прекратить отслеживание ресурса\n"
    "/list — список отслеживаемых ресурсов"
)


async def help_handler(event: events.NewMessage.Event) -> None:
    await event.respond(_HELP_TEXT)
    raise events.StopPropagation
