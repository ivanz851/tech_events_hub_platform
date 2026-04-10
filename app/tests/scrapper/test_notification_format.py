from src.scrapper.models import EventData
from src.scrapper.notification.formatter import format_event_notification


def test_format_with_full_event_data() -> None:
    event = EventData(
        title="Python Meetup",
        event_date="2026-05-01 18:00",
        location="Moscow, Skolkovo",
        price="Бесплатно",
        registration_url="https://meetup.com/register",
        format="Офлайн",
        event_type="митап",
        summary="Встреча Python разработчиков",
        tags=["Python", "backend"],
        organizer="JetBrains",
    )
    msg = format_event_notification("https://t.me/python_meetup", event)

    assert "https://t.me/python_meetup" in msg
    assert "Python Meetup" in msg
    assert "2026-05-01 18:00" in msg
    assert "Moscow, Skolkovo" in msg
    assert "Бесплатно" in msg
    assert "Офлайн" in msg
    assert "митап" in msg
    assert "Встреча Python разработчиков" in msg
    assert "Python" in msg
    assert "backend" in msg
    assert "JetBrains" in msg
    assert "https://meetup.com/register" in msg


def test_format_with_minimal_event_data() -> None:
    event = EventData()
    msg = format_event_notification("https://t.me/ch", event)

    assert "https://t.me/ch" in msg
    assert "не указано" in msg


def test_format_without_optional_fields() -> None:
    event = EventData(title="Hackathon", event_date="2026-06-10 09:00")
    msg = format_event_notification("https://t.me/hack", event)

    assert "Hackathon" in msg
    assert "2026-06-10 09:00" in msg
    assert "Организатор" not in msg
    assert "Теги" not in msg
    assert "Регистрация" not in msg


def test_format_different_update_types() -> None:
    conference = EventData(event_type="конференция", title="PyCon RU")
    workshop = EventData(event_type="воркшоп", title="FastAPI Workshop")

    conf_msg = format_event_notification("https://t.me/pycon", conference)
    work_msg = format_event_notification("https://t.me/ws", workshop)

    assert "конференция" in conf_msg
    assert "PyCon RU" in conf_msg
    assert "воркшоп" in work_msg
    assert "FastAPI Workshop" in work_msg
