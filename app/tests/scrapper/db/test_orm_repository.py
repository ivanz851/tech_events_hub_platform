import pytest

from src.scrapper.models import EventData
from src.scrapper.repository.orm_repository import OrmLinkRepository
from src.scrapper.server import _build_repository
from src.scrapper.settings import ScrapperSettings


@pytest.mark.asyncio
async def test_register_chat(orm_repository: OrmLinkRepository) -> None:
    assert await orm_repository.register_chat(10001) is True
    assert await orm_repository.chat_exists(10001) is True


@pytest.mark.asyncio
async def test_register_chat_duplicate(orm_repository: OrmLinkRepository) -> None:
    await orm_repository.register_chat(10002)
    assert await orm_repository.register_chat(10002) is False


@pytest.mark.asyncio
async def test_delete_chat(orm_repository: OrmLinkRepository) -> None:
    await orm_repository.register_chat(10003)
    assert await orm_repository.delete_chat(10003) is True
    assert await orm_repository.chat_exists(10003) is False


@pytest.mark.asyncio
async def test_delete_nonexistent_chat(orm_repository: OrmLinkRepository) -> None:
    assert await orm_repository.delete_chat(99999) is False


@pytest.mark.asyncio
async def test_add_and_get_link(orm_repository: OrmLinkRepository) -> None:
    await orm_repository.register_chat(10004)
    record = await orm_repository.add_link(10004, "https://t.me/orm_ch", ["py"], [])
    assert record is not None
    assert record.url == "https://t.me/orm_ch"
    assert record.tags == ["py"]

    links = await orm_repository.get_links(10004)
    assert len(links) == 1
    assert links[0].url == "https://t.me/orm_ch"


@pytest.mark.asyncio
async def test_add_link_duplicate(orm_repository: OrmLinkRepository) -> None:
    await orm_repository.register_chat(10005)
    await orm_repository.add_link(10005, "https://t.me/orm_dup", [], [])
    assert await orm_repository.add_link(10005, "https://t.me/orm_dup", [], []) is None


@pytest.mark.asyncio
async def test_add_link_unknown_chat(orm_repository: OrmLinkRepository) -> None:
    assert await orm_repository.add_link(88888, "https://t.me/orm_x", [], []) is None


@pytest.mark.asyncio
async def test_remove_link(orm_repository: OrmLinkRepository) -> None:
    await orm_repository.register_chat(10006)
    await orm_repository.add_link(10006, "https://t.me/orm_rm", [], [])
    record = await orm_repository.remove_link(10006, "https://t.me/orm_rm")
    assert record is not None
    assert record.url == "https://t.me/orm_rm"
    assert len(await orm_repository.get_links(10006)) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_link(orm_repository: OrmLinkRepository) -> None:
    await orm_repository.register_chat(10007)
    assert await orm_repository.remove_link(10007, "https://t.me/nope") is None


@pytest.mark.asyncio
async def test_get_tracked_links_page(orm_repository: OrmLinkRepository) -> None:
    await orm_repository.register_chat(10008)
    await orm_repository.register_chat(10009)
    await orm_repository.add_link(10008, "https://t.me/shared_orm", [], [])
    await orm_repository.add_link(10009, "https://t.me/shared_orm", [], [])

    page = await orm_repository.get_tracked_links_page(0, 10)
    shared = next((t for t in page if t.url == "https://t.me/shared_orm"), None)
    assert shared is not None
    assert set(shared.chat_ids) == {10008, 10009}


@pytest.mark.asyncio
async def test_save_event_data(orm_repository: OrmLinkRepository) -> None:
    await orm_repository.register_chat(10010)
    record = await orm_repository.add_link(10010, "https://t.me/event_orm", [], [])
    assert record is not None
    event = EventData(title="Test Event", summary="A great event", tags=["Python"])
    await orm_repository.save_event_data(record.id, event)


def test_config_selects_orm(settings_orm: ScrapperSettings) -> None:
    repo = _build_repository(settings_orm)
    assert isinstance(repo, OrmLinkRepository)
