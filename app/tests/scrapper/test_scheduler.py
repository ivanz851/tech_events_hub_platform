from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
import pytest_asyncio

from src.scrapper.notification.router import NotificationRouter
from src.scrapper.repository.in_memory import InMemoryLinkRepository
from src.scrapper.scheduler import Scheduler
from src.scrapper.telegram_scrapper import TelegramChannelScrapper


def _make_message(msg_id: int) -> MagicMock:
    m = MagicMock()
    m.id = msg_id
    m.text = None
    return m


def _make_scrapper(messages: list[MagicMock] | None = None) -> AsyncMock:
    scrapper = AsyncMock(spec=TelegramChannelScrapper)
    scrapper.get_new_messages = AsyncMock(return_value=messages or [])
    return scrapper


@pytest_asyncio.fixture
async def repository() -> InMemoryLinkRepository:
    repo = InMemoryLinkRepository()
    await repo.register_chat(1)
    await repo.register_chat(2)
    return repo


@pytest_asyncio.fixture
async def user_ids(repository: InMemoryLinkRepository) -> tuple[UUID, UUID]:
    uid1 = await repository.get_or_create_by_telegram(1)
    uid2 = await repository.get_or_create_by_telegram(2)
    return uid1, uid2


@pytest.fixture
def notification() -> AsyncMock:
    return AsyncMock(spec=NotificationRouter)


@pytest.mark.asyncio
async def test_scheduler_notifies_only_subscribed_users(
    repository: InMemoryLinkRepository,
    user_ids: tuple[UUID, UUID],
    notification: AsyncMock,
) -> None:
    uid1, uid2 = user_ids
    await repository.add_link(uid1, "https://t.me/url_a")
    await repository.add_link(uid2, "https://t.me/url_b")
    await repository.add_link(uid1, "https://t.me/url_c")
    await repository.add_link(uid2, "https://t.me/url_c")

    scrapper = _make_scrapper([_make_message(100)])
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)
    await scheduler._check_and_notify()
    notification.route.assert_not_called()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(101)])
    await scheduler._check_and_notify()

    calls = notification.route.call_args_list
    sent_map: dict[str, set[UUID]] = {}
    for call in calls:
        url = call.kwargs["url"]
        ids = set(call.kwargs["user_ids"])
        sent_map[url] = ids

    assert sent_map["https://t.me/url_a"] == {uid1}
    assert sent_map["https://t.me/url_b"] == {uid2}
    assert sent_map["https://t.me/url_c"] == {uid1, uid2}


@pytest.mark.asyncio
async def test_scheduler_no_new_messages_no_notification(
    repository: InMemoryLinkRepository,
    user_ids: tuple[UUID, UUID],
    notification: AsyncMock,
) -> None:
    uid1, _ = user_ids
    await repository.add_link(uid1, "https://t.me/ch")
    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()
    scrapper.get_new_messages = AsyncMock(return_value=[])
    await scheduler._check_and_notify()

    notification.route.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_no_tracked_links_no_notifications(
    notification: AsyncMock,
) -> None:
    repository = InMemoryLinkRepository()
    scrapper = _make_scrapper()
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()
    notification.route.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_notification_error_does_not_crash(
    repository: InMemoryLinkRepository,
    user_ids: tuple[UUID, UUID],
    notification: AsyncMock,
) -> None:
    uid1, _ = user_ids
    await repository.add_link(uid1, "https://t.me/ch")
    notification.route = AsyncMock(side_effect=Exception("routing error"))

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)
    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11)])
    await scheduler._check_and_notify()


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_same_message_twice(
    repository: InMemoryLinkRepository,
    user_ids: tuple[UUID, UUID],
    notification: AsyncMock,
) -> None:
    uid1, _ = user_ids
    await repository.add_link(uid1, "https://t.me/ch")
    notification.route = AsyncMock()

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11)])
    await scheduler._check_and_notify()
    assert notification.route.call_count == 1

    await scheduler._check_and_notify()
    assert notification.route.call_count == 1
