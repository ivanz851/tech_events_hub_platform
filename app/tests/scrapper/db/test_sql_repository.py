import pytest

from src.scrapper.models import EventData
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
async def test_add_and_get_link(sql_repository: SqlLinkRepository) -> None:
    await sql_repository.register_chat(20004)
    record = await sql_repository.add_link(20004, "https://t.me/sql_ch", ["go"], [])
    assert record is not None
    assert record.url == "https://t.me/sql_ch"
    assert record.tags == ["go"]

    links = await sql_repository.get_links(20004)
    assert len(links) == 1
    assert links[0].url == "https://t.me/sql_ch"


@pytest.mark.asyncio
async def test_add_link_duplicate(sql_repository: SqlLinkRepository) -> None:
    await sql_repository.register_chat(20005)
    await sql_repository.add_link(20005, "https://t.me/sql_dup", [], [])
    assert await sql_repository.add_link(20005, "https://t.me/sql_dup", [], []) is None


@pytest.mark.asyncio
async def test_add_link_unknown_chat(sql_repository: SqlLinkRepository) -> None:
    assert await sql_repository.add_link(77777, "https://t.me/sql_x", [], []) is None


@pytest.mark.asyncio
async def test_remove_link(sql_repository: SqlLinkRepository) -> None:
    await sql_repository.register_chat(20006)
    await sql_repository.add_link(20006, "https://t.me/sql_rm", [], [])
    record = await sql_repository.remove_link(20006, "https://t.me/sql_rm")
    assert record is not None
    assert record.url == "https://t.me/sql_rm"
    assert len(await sql_repository.get_links(20006)) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_link(sql_repository: SqlLinkRepository) -> None:
    await sql_repository.register_chat(20007)
    assert await sql_repository.remove_link(20007, "https://t.me/nope_sql") is None


@pytest.mark.asyncio
async def test_get_tracked_links_page(sql_repository: SqlLinkRepository) -> None:
    await sql_repository.register_chat(20008)
    await sql_repository.register_chat(20009)
    await sql_repository.add_link(20008, "https://t.me/shared_sql", [], [])
    await sql_repository.add_link(20009, "https://t.me/shared_sql", [], [])

    page = await sql_repository.get_tracked_links_page(0, 10)
    shared = next((t for t in page if t.url == "https://t.me/shared_sql"), None)
    assert shared is not None
    assert set(shared.chat_ids) == {20008, 20009}


@pytest.mark.asyncio
async def test_save_event_data(sql_repository: SqlLinkRepository) -> None:
    await sql_repository.register_chat(20010)
    record = await sql_repository.add_link(20010, "https://t.me/event_sql", [], [])
    assert record is not None
    event = EventData(title="SQL Event", summary="Raw SQL event", tags=["Go"])
    await sql_repository.save_event_data(record.id, event)


def test_config_selects_sql(settings_sql: ScrapperSettings) -> None:
    repo = _build_repository(settings_sql)
    assert isinstance(repo, SqlLinkRepository)
