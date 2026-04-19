import pytest

from src.scrapper.models import EventData, SubscriptionFilters
from src.scrapper.repository.sql_repository import SqlLinkRepository
from src.scrapper.server import _build_repository
from src.scrapper.settings import ScrapperSettings


@pytest.mark.asyncio
async def test_register_chat(sql_repository: SqlLinkRepository) -> None:
    assert await sql_repository.register_chat(20001) is True
    assert await sql_repository.chat_exists(20001) is True


@pytest.mark.asyncio
async def test_register_chat_duplicate(sql_repository: SqlLinkRepository) -> None:
    await sql_repository.register_chat(20002)
    assert await sql_repository.register_chat(20002) is False


@pytest.mark.asyncio
async def test_delete_chat(sql_repository: SqlLinkRepository) -> None:
    await sql_repository.register_chat(20003)
    assert await sql_repository.delete_chat(20003) is True
    assert await sql_repository.chat_exists(20003) is False


@pytest.mark.asyncio
async def test_delete_nonexistent_chat(sql_repository: SqlLinkRepository) -> None:
    assert await sql_repository.delete_chat(99998) is False


@pytest.mark.asyncio
async def test_get_or_create_by_telegram(sql_repository: SqlLinkRepository) -> None:
    uid1 = await sql_repository.get_or_create_by_telegram(21001)
    uid2 = await sql_repository.get_or_create_by_telegram(21001)
    assert uid1 == uid2


@pytest.mark.asyncio
async def test_get_or_create_by_yandex(sql_repository: SqlLinkRepository) -> None:
    uid1 = await sql_repository.get_or_create_by_yandex("ya-sql-1", "b@ya.ru")
    uid2 = await sql_repository.get_or_create_by_yandex("ya-sql-1", None)
    assert uid1 == uid2


@pytest.mark.asyncio
async def test_add_and_get_link(sql_repository: SqlLinkRepository) -> None:
    user_id = await sql_repository.get_or_create_by_telegram(20004)
    filters = SubscriptionFilters(categories=["go"])
    record = await sql_repository.add_link(user_id, "https://t.me/sql_ch", filters)
    assert record is not None
    assert record.url == "https://t.me/sql_ch"
    assert record.filters is not None
    assert record.filters.categories == ["go"]

    links = await sql_repository.get_links(user_id)
    assert len(links) == 1
    assert links[0].url == "https://t.me/sql_ch"


@pytest.mark.asyncio
async def test_add_link_duplicate(sql_repository: SqlLinkRepository) -> None:
    user_id = await sql_repository.get_or_create_by_telegram(20005)
    await sql_repository.add_link(user_id, "https://t.me/sql_dup")
    assert await sql_repository.add_link(user_id, "https://t.me/sql_dup") is None


@pytest.mark.asyncio
async def test_remove_link(sql_repository: SqlLinkRepository) -> None:
    user_id = await sql_repository.get_or_create_by_telegram(20006)
    await sql_repository.add_link(user_id, "https://t.me/sql_rm")
    record = await sql_repository.remove_link(user_id, "https://t.me/sql_rm")
    assert record is not None
    assert record.url == "https://t.me/sql_rm"
    assert len(await sql_repository.get_links(user_id)) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_link(sql_repository: SqlLinkRepository) -> None:
    user_id = await sql_repository.get_or_create_by_telegram(20007)
    assert await sql_repository.remove_link(user_id, "https://t.me/nope_sql") is None


@pytest.mark.asyncio
async def test_get_tracked_links_page(sql_repository: SqlLinkRepository) -> None:
    uid1 = await sql_repository.get_or_create_by_telegram(20008)
    uid2 = await sql_repository.get_or_create_by_telegram(20009)
    await sql_repository.add_link(uid1, "https://t.me/shared_sql")
    await sql_repository.add_link(uid2, "https://t.me/shared_sql")

    page = await sql_repository.get_tracked_links_page(0, 10)
    shared = next((t for t in page if t.url == "https://t.me/shared_sql"), None)
    assert shared is not None
    tg_ids = {sub.tg_chat_id for sub in shared.subscribers if sub.tg_chat_id is not None}
    assert tg_ids == {20008, 20009}


@pytest.mark.asyncio
async def test_get_tracked_links_page_includes_filters(sql_repository: SqlLinkRepository) -> None:
    uid = await sql_repository.get_or_create_by_telegram(20011)
    await sql_repository.add_link(uid, "https://t.me/filt_sql", SubscriptionFilters(city="SPb"))

    page = await sql_repository.get_tracked_links_page(0, 10)
    entry = next((t for t in page if t.url == "https://t.me/filt_sql"), None)
    assert entry is not None
    sub = next(s for s in entry.subscribers if s.tg_chat_id == 20011)
    assert sub.filters is not None
    assert sub.filters.city == "SPb"


@pytest.mark.asyncio
async def test_save_event_data(sql_repository: SqlLinkRepository) -> None:
    user_id = await sql_repository.get_or_create_by_telegram(20010)
    record = await sql_repository.add_link(user_id, "https://t.me/event_sql")
    assert record is not None
    event = EventData(title="SQL Event", summary="Raw SQL event", tags=["Go"])
    await sql_repository.save_event_data(record.id, event)


@pytest.mark.asyncio
async def test_link_telegram_to_user(sql_repository: SqlLinkRepository) -> None:
    user_id = await sql_repository.get_or_create_by_yandex("ya-sql-link", "c@ya.ru")
    await sql_repository.link_telegram_to_user(user_id, 31001)
    uid_found = await sql_repository.get_or_create_by_telegram(31001)
    assert uid_found == user_id


def test_config_selects_sql(settings_sql: ScrapperSettings) -> None:
    repo = _build_repository(settings_sql)
    assert isinstance(repo, SqlLinkRepository)
