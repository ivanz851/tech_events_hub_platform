from unittest.mock import AsyncMock, MagicMock

import pytest

from src.scrapper.models import SubscriptionFilters
from src.scrapper.notification.router import NotificationRouter
from src.scrapper.repository.in_memory import InMemoryLinkRepository
from src.scrapper.scheduler import Scheduler
from src.scrapper.telegram_scrapper import TelegramChannelScrapper


def _make_message(msg_id: int, text: str = "Announcement") -> MagicMock:
    m = MagicMock()
    m.id = msg_id
    m.text = text
    return m


@pytest.mark.asyncio
async def test_scheduler_sends_only_to_matched_subscribers() -> None:
    repo = InMemoryLinkRepository()
    url = "https://t.me/filterchan"

    uid1 = await repo.get_or_create_by_telegram(101)
    await repo.add_link(uid1, url, SubscriptionFilters())

    uid2 = await repo.get_or_create_by_telegram(102)
    await repo.add_link(uid2, url, SubscriptionFilters(city="Berlin"))

    uid3 = await repo.get_or_create_by_telegram(103)
    await repo.add_link(uid3, url)

    notification = AsyncMock(spec=NotificationRouter)
    tg_scrapper = AsyncMock(spec=TelegramChannelScrapper)
    tg_scrapper.get_new_messages = AsyncMock(return_value=[_make_message(10)])

    scheduler = Scheduler(
        repository=repo,
        notification=notification,
        tg_scrapper=tg_scrapper,
        interval_seconds=9999,
    )

    await scheduler._check_and_notify()
    notification.route.assert_not_called()

    tg_scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11, "New event!")])
    await scheduler._check_and_notify()

    notification.route.assert_called_once()
    call_kwargs = notification.route.call_args.kwargs
    assert call_kwargs["url"] == url
    assert set(call_kwargs["user_ids"]) == {uid1, uid3}
    assert uid2 not in call_kwargs["user_ids"]
