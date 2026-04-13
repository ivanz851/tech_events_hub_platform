from unittest.mock import AsyncMock

import pytest

from src.scrapper.notification.abstract import AbstractNotificationService, NotificationError
from src.scrapper.notification.fallback import FallbackNotificationService


@pytest.mark.asyncio
async def test_fallback_not_called_when_primary_succeeds() -> None:
    primary = AsyncMock(spec=AbstractNotificationService)
    fallback = AsyncMock(spec=AbstractNotificationService)

    svc = FallbackNotificationService(primary, fallback)
    await svc.send_update(1, "https://t.me/ch", "desc", [1])

    primary.send_update.assert_called_once()
    fallback.send_update.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_called_when_primary_fails() -> None:
    primary = AsyncMock(spec=AbstractNotificationService)
    primary.send_update.side_effect = NotificationError("primary failed")
    fallback = AsyncMock(spec=AbstractNotificationService)

    svc = FallbackNotificationService(primary, fallback)
    await svc.send_update(1, "https://t.me/ch", "desc", [1])

    primary.send_update.assert_called_once()
    fallback.send_update.assert_called_once()


@pytest.mark.asyncio
async def test_raises_when_both_fail() -> None:
    primary = AsyncMock(spec=AbstractNotificationService)
    primary.send_update.side_effect = NotificationError("primary failed")
    fallback = AsyncMock(spec=AbstractNotificationService)
    fallback.send_update.side_effect = NotificationError("fallback failed")

    svc = FallbackNotificationService(primary, fallback)
    with pytest.raises(NotificationError):
        await svc.send_update(1, "https://t.me/ch", "desc", [1])


@pytest.mark.asyncio
async def test_fallback_receives_same_arguments() -> None:
    primary = AsyncMock(spec=AbstractNotificationService)
    primary.send_update.side_effect = NotificationError("primary failed")
    fallback = AsyncMock(spec=AbstractNotificationService)

    svc = FallbackNotificationService(primary, fallback)
    await svc.send_update(update_id=42, url="https://t.me/x", description="ev", tg_chat_ids=[7])

    fallback.send_update.assert_called_once_with(42, "https://t.me/x", "ev", [7])
