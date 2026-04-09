from unittest.mock import AsyncMock, MagicMock

import pytest

from src.scrapper.clients.bot import BotClient, BotClientError
from src.scrapper.repository.storage import InMemoryStorage
from src.scrapper.scheduler import Scheduler
from src.scrapper.telegram_scrapper import TelegramChannelScrapper


def _make_message(msg_id: int) -> MagicMock:
    m = MagicMock()
    m.id = msg_id
    return m


def _make_scrapper(messages: list[MagicMock] | None = None) -> AsyncMock:
    scrapper = AsyncMock(spec=TelegramChannelScrapper)
    scrapper.get_new_messages = AsyncMock(return_value=messages or [])
    return scrapper


@pytest.fixture
def storage() -> InMemoryStorage:
    s = InMemoryStorage()
    s.register_chat(1)
    s.register_chat(2)
    return s


@pytest.fixture
def bot_client() -> AsyncMock:
    return AsyncMock(spec=BotClient)


@pytest.mark.asyncio
async def test_scheduler_notifies_only_subscribed_users(
    storage: InMemoryStorage,
    bot_client: AsyncMock,
) -> None:
    storage.add_link(1, "https://t.me/url_a", [], [])
    storage.add_link(2, "https://t.me/url_b", [], [])
    storage.add_link(1, "https://t.me/url_c", [], [])
    storage.add_link(2, "https://t.me/url_c", [], [])

    bot_client.send_update = AsyncMock()

    scrapper = _make_scrapper([_make_message(100)])
    scheduler = Scheduler(storage, bot_client, scrapper, interval_seconds=9999)
    await scheduler._check_and_notify()
    bot_client.send_update.assert_not_called()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(101)])
    await scheduler._check_and_notify()

    calls = bot_client.send_update.call_args_list
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
    storage: InMemoryStorage,
    bot_client: AsyncMock,
) -> None:
    storage.add_link(1, "https://t.me/ch", [], [])
    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(storage, bot_client, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()
    scrapper.get_new_messages = AsyncMock(return_value=[])
    await scheduler._check_and_notify()

    bot_client.send_update.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_no_tracked_links_no_notifications(
    bot_client: AsyncMock,
) -> None:
    storage = InMemoryStorage()
    scrapper = _make_scrapper()
    scheduler = Scheduler(storage, bot_client, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()
    bot_client.send_update.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_bot_error_does_not_crash(
    storage: InMemoryStorage,
    bot_client: AsyncMock,
) -> None:
    storage.add_link(1, "https://t.me/ch", [], [])
    bot_client.send_update = AsyncMock(side_effect=BotClientError(500, "server error"))

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(storage, bot_client, scrapper, interval_seconds=9999)
    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11)])
    await scheduler._check_and_notify()


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_same_message_twice(
    storage: InMemoryStorage,
    bot_client: AsyncMock,
) -> None:
    storage.add_link(1, "https://t.me/ch", [], [])
    bot_client.send_update = AsyncMock()

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(storage, bot_client, scrapper, interval_seconds=9999)

    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11)])
    await scheduler._check_and_notify()
    assert bot_client.send_update.call_count == 1

    await scheduler._check_and_notify()
    assert bot_client.send_update.call_count == 1
