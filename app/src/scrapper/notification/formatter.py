from src.scrapper.models import EventData

__all__ = ("format_event_notification",)

_ABSENT = "не указано"


def format_event_notification(url: str, event: EventData) -> str:
    lines: list[str] = [f"Новое событие из {url}"]
    lines.append(f"Название: {event.title or _ABSENT}")
    lines.append(f"Дата: {event.event_date or _ABSENT}")
    lines.append(f"Место: {event.location or _ABSENT}")
    lines.append(f"Стоимость: {event.price or _ABSENT}")
    lines.append(f"Формат: {event.format or _ABSENT}")
    lines.append(f"Тип: {event.event_type or _ABSENT}")
    if event.summary:
        lines.append(f"О мероприятии: {event.summary}")
    if event.tags:
        lines.append(f"Теги: {', '.join(event.tags)}")
    if event.organizer:
        lines.append(f"Организатор: {event.organizer}")
    if event.registration_url:
        lines.append(f"Регистрация: {event.registration_url}")
    return "\n".join(lines)
