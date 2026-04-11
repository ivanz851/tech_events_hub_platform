from telethon import events

from src.cache.notify_mode_store import NotifyModeStore

__all__ = ("make_notify_handler",)

_LABELS: dict[str, str] = {"immediate": "Сразу", "digest": "Дайджест раз в сутки"}
_VALID_MODES = frozenset(_LABELS)


def make_notify_handler(notify_mode_store: NotifyModeStore) -> events.NewMessage:
    async def notify_handler(event: events.NewMessage.Event) -> None:
        chat_id: int = event.chat_id
        text: str = event.raw_text.strip()
        parts = text.split(maxsplit=1)

        if len(parts) == 1:
            mode = await notify_mode_store.get(chat_id)
            label = _LABELS.get(mode, mode)
            await event.respond(
                f"Текущий режим: {label}\nСменить: /notify immediate, /notify digest",
            )
        elif parts[1] in _VALID_MODES:
            await notify_mode_store.set(chat_id, parts[1])
            await event.respond(f"Режим уведомлений: {_LABELS[parts[1]]}")
        else:
            await event.respond("Допустимые значения: immediate, digest")

        raise events.StopPropagation

    return notify_handler  # type: ignore[return-value]
