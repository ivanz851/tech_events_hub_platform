from unittest.mock import AsyncMock, MagicMock

import pytest

from src.scrapper.llm.client import LLMEventResult
from src.scrapper.notification.abstract import AbstractNotificationService
from src.scrapper.repository.in_memory import InMemoryLinkRepository
from src.scrapper.scheduler import Scheduler
from src.scrapper.telegram_scrapper import TelegramChannelScrapper


def _make_message(msg_id: int, text: str = "Some announcement") -> MagicMock:
    m = MagicMock()
    m.id = msg_id
    m.text = text
    return m


def _make_scrapper(messages: list[MagicMock] | None = None) -> AsyncMock:
    scrapper = AsyncMock(spec=TelegramChannelScrapper)
    scrapper.get_new_messages = AsyncMock(return_value=messages or [])
    return scrapper


async def _make_repo_with_link(chat_id: int, url: str) -> InMemoryLinkRepository:
    repo = InMemoryLinkRepository()
    await repo.register_chat(chat_id)
    user_id = await repo.get_or_create_by_telegram(chat_id)
    await repo.add_link(user_id, url, [], [])
    return repo


@pytest.mark.asyncio
async def test_is_event_false_skips_notification() -> None:
    repo = await _make_repo_with_link(1, "https://t.me/testchannel")
    notification = AsyncMock(spec=AbstractNotificationService)

    llm_client = MagicMock()
    llm_client.analyze = AsyncMock(return_value=LLMEventResult(is_event=False))

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(
        repository=repo,
        notification=notification,
        tg_scrapper=scrapper,
        llm_client=llm_client,
        interval_seconds=9999,
    )

    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11, "Sale: 50% off shoes!")])
    await scheduler._check_and_notify()

    notification.send_update.assert_not_called()
    llm_client.analyze.assert_called_once()


@pytest.mark.asyncio
async def test_is_event_true_sends_notification() -> None:
    repo = await _make_repo_with_link(1, "https://t.me/testchannel")
    notification = AsyncMock(spec=AbstractNotificationService)

    llm_client = MagicMock()
    llm_client.analyze = AsyncMock(
        return_value=LLMEventResult(
            is_event=True,
            title="PyCon 2025",
            summary="Big Python conference",
        ),
    )

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(
        repository=repo,
        notification=notification,
        tg_scrapper=scrapper,
        llm_client=llm_client,
        interval_seconds=9999,
    )

    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11, "PyCon 2025 — join us!")])
    await scheduler._check_and_notify()

    notification.send_update.assert_called_once()
    call_kwargs = notification.send_update.call_args.kwargs
    assert call_kwargs["url"] == "https://t.me/testchannel"
    assert call_kwargs["tg_chat_ids"] == [1]


@pytest.mark.asyncio
async def test_no_llm_client_always_sends_notification() -> None:
    repo = await _make_repo_with_link(1, "https://t.me/testchannel")
    notification = AsyncMock(spec=AbstractNotificationService)

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(
        repository=repo,
        notification=notification,
        tg_scrapper=scrapper,
        llm_client=None,
        interval_seconds=9999,
    )

    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11, "Random text")])
    await scheduler._check_and_notify()

    notification.send_update.assert_called_once()


@pytest.mark.asyncio
async def test_llm_analyze_none_skips_notification() -> None:
    repo = await _make_repo_with_link(1, "https://t.me/testchannel")
    notification = AsyncMock(spec=AbstractNotificationService)

    llm_client = MagicMock()
    llm_client.analyze = AsyncMock(return_value=None)

    scrapper = _make_scrapper([_make_message(10)])
    scheduler = Scheduler(
        repository=repo,
        notification=notification,
        tg_scrapper=scrapper,
        llm_client=llm_client,
        interval_seconds=9999,
    )

    await scheduler._check_and_notify()

    scrapper.get_new_messages = AsyncMock(return_value=[_make_message(11, "Some text")])
    await scheduler._check_and_notify()

    notification.send_update.assert_not_called()
