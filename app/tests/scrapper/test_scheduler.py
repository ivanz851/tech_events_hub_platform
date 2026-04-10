from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.scrapper.notification.abstract import AbstractNotificationService, NotificationError
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


@pytest.fixture
def notification() -> AsyncMock:
    return AsyncMock(spec=AbstractNotificationService)


@pytest.mark.asyncio
async def test_scheduler_notifies_only_subscribed_users(
    repository: InMemoryLinkRepository,
    notification: AsyncMock,
) -> None:
    await repository.add_link(1, "https://t.me/url_a", [], [])
    await repository.add_link(2, "https://t.me/url_b", [], [])
    await repository.add_link(1, "https://t.me/url_c", [], [])
    await repository.add_link(2, "https://t.me/url_c", [], [])

    scrapper = _make_scrapper([_make_message(100)])
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)
    await scheduler._check_and_notify()
    notification.send_update.assert_not_called()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(101)])
    await scheduler._check_and_notify()

    calls = notification.send_update.call_args_list
    sent_map: dict[str, set[int]] = {}
    for call in calls:
        url = call.kwargs["url"]
        chat_ids = set(call.kwargs["tg_chat_ids"])
        sent_map[url] = chat_ids

    assert sent_map["https://t.me/url_a"] == {1}
    assert sent_map["https://t.me/url_b"] == {2}
    assert sent_map["https://t.me/url_c"] == {1, 2}


@pytest.mark.asyncio
async def test_scheduler_no_new_messages_no_notification(
    repository: InMemoryLinkRepository,
    notification: AsyncMock,
) -> None:
    await repository.add_link(1, "https://t.me/ch", [], [])
    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()
    scrapper.get_new_messages = AsyncMock(return_value=[])
    await scheduler._check_and_notify()

    notification.send_update.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_no_tracked_links_no_notifications(
    notification: AsyncMock,
) -> None:
    repository = InMemoryLinkRepository()
    scrapper = _make_scrapper()
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()
    notification.send_update.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_notification_error_does_not_crash(
    repository: InMemoryLinkRepository,
    notification: AsyncMock,
) -> None:
    await repository.add_link(1, "https://t.me/ch", [], [])
    notification.send_update = AsyncMock(side_effect=NotificationError("server error"))

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)
    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11)])
    await scheduler._check_and_notify()


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_same_message_twice(
    repository: InMemoryLinkRepository,
    notification: AsyncMock,
) -> None:
    await repository.add_link(1, "https://t.me/ch", [], [])
    notification.send_update = AsyncMock()

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(repository, notification, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11)])
    await scheduler._check_and_notify()
    assert notification.send_update.call_count == 1

    await scheduler._check_and_notify()
    assert notification.send_update.call_count == 1
