import uuid
from unittest.mock import AsyncMock

import pytest

from src.scrapper.models import EventData, RouteInfo
from src.scrapper.notification.abstract import AbstractNotificationService
from src.scrapper.notification.email_notification import EmailNotificationService
from src.scrapper.notification.router import NotificationRouter


def _make_uid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_router_dispatches_telegram_and_email_correctly() -> None:
    uid_a = _make_uid()
    uid_b = _make_uid()
    uid_c = _make_uid()
    tg_a = 111
    tg_c = 333

    repository = AsyncMock()
    repository.get_notification_routes.return_value = [
        RouteInfo(
            user_id=uid_a,
            tg_chat_id=tg_a,
            email=None,
            notify_telegram=True,
            notify_email=False,
        ),
        RouteInfo(
            user_id=uid_b,
            tg_chat_id=None,
            email="b@example.com",
            notify_telegram=False,
            notify_email=True,
        ),
        RouteInfo(
            user_id=uid_c,
            tg_chat_id=tg_c,
            email="c@example.com",
            notify_telegram=True,
            notify_email=True,
        ),
    ]

    telegram_service = AsyncMock(spec=AbstractNotificationService)
    email_service = AsyncMock(spec=EmailNotificationService)

    router = NotificationRouter(repository, telegram_service, email_service)
    event = EventData(title="PyCon 2025", summary="A great event")

    await router.route(
        update_id=1,
        url="https://t.me/test",
        description="PyCon 2025",
        user_ids=[uid_a, uid_b, uid_c],
        event=event,
    )

    telegram_service.send_update.assert_called_once()
    tg_call_kwargs = telegram_service.send_update.call_args.kwargs
    assert set(tg_call_kwargs["tg_chat_ids"]) == {tg_a, tg_c}

    email_service.send_emails.assert_called_once()
    email_call_args = email_service.send_emails.call_args
    sent_emails = set(email_call_args.args[0])
    assert sent_emails == {"b@example.com", "c@example.com"}


@pytest.mark.asyncio
async def test_router_skips_telegram_when_no_eligible_users() -> None:
    uid = _make_uid()
    repository = AsyncMock()
    repository.get_notification_routes.return_value = [
        RouteInfo(
            user_id=uid,
            tg_chat_id=None,
            email="only@email.com",
            notify_telegram=False,
            notify_email=True,
        ),
    ]

    telegram_service = AsyncMock(spec=AbstractNotificationService)
    email_service = AsyncMock(spec=EmailNotificationService)

    router = NotificationRouter(repository, telegram_service, email_service)
    await router.route(1, "https://example.com", "desc", [uid], EventData())

    telegram_service.send_update.assert_not_called()
    email_service.send_emails.assert_called_once()


@pytest.mark.asyncio
async def test_router_telegram_error_does_not_block_email() -> None:
    from src.scrapper.notification.abstract import NotificationError

    uid = _make_uid()
    repository = AsyncMock()
    repository.get_notification_routes.return_value = [
        RouteInfo(
            user_id=uid,
            tg_chat_id=100,
            email="user@example.com",
            notify_telegram=True,
            notify_email=True,
        ),
    ]

    telegram_service = AsyncMock(spec=AbstractNotificationService)
    telegram_service.send_update.side_effect = NotificationError("tg failed")
    email_service = AsyncMock(spec=EmailNotificationService)

    router = NotificationRouter(repository, telegram_service, email_service)
    await router.route(1, "https://example.com", "desc", [uid], EventData())

    email_service.send_emails.assert_called_once()


@pytest.mark.asyncio
async def test_router_empty_user_ids_does_nothing() -> None:
    repository = AsyncMock()
    telegram_service = AsyncMock(spec=AbstractNotificationService)
    email_service = AsyncMock(spec=EmailNotificationService)

    router = NotificationRouter(repository, telegram_service, email_service)
    await router.route(1, "https://example.com", "desc", [], EventData())

    repository.get_notification_routes.assert_not_called()
    telegram_service.send_update.assert_not_called()
    email_service.send_emails.assert_not_called()
