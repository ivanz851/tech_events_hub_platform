import pytest

from src.scrapper.repository.storage import InMemoryStorage


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


def test_register_chat(storage: InMemoryStorage) -> None:
    assert storage.register_chat(1) is True
    assert storage.chat_exists(1)


def test_register_chat_duplicate(storage: InMemoryStorage) -> None:
    storage.register_chat(1)
    assert storage.register_chat(1) is False


def test_delete_chat(storage: InMemoryStorage) -> None:
    storage.register_chat(1)
    assert storage.delete_chat(1) is True
    assert not storage.chat_exists(1)


def test_delete_nonexistent_chat(storage: InMemoryStorage) -> None:
    assert storage.delete_chat(999) is False


def test_add_link(storage: InMemoryStorage) -> None:
    storage.register_chat(1)
    record = storage.add_link(1, "https://t.me/ch", ["py"], [])
    assert record is not None
    assert record.url == "https://t.me/ch"
    assert record.tags == ["py"]


def test_add_link_duplicate_returns_none(storage: InMemoryStorage) -> None:
    storage.register_chat(1)
    storage.add_link(1, "https://t.me/ch", [], [])
    result = storage.add_link(1, "https://t.me/ch", [], [])
    assert result is None


def test_add_link_unknown_chat_returns_none(storage: InMemoryStorage) -> None:
    result = storage.add_link(999, "https://t.me/ch", [], [])
    assert result is None


def test_remove_link(storage: InMemoryStorage) -> None:
    storage.register_chat(1)
    storage.add_link(1, "https://t.me/ch", [], [])
    record = storage.remove_link(1, "https://t.me/ch")
    assert record is not None
    assert record.url == "https://t.me/ch"
    assert len(storage.get_links(1)) == 0


def test_remove_nonexistent_link(storage: InMemoryStorage) -> None:
    storage.register_chat(1)
    assert storage.remove_link(1, "https://t.me/nope") is None


def test_get_links_returns_all(storage: InMemoryStorage) -> None:
    storage.register_chat(1)
    storage.add_link(1, "https://t.me/ch1", [], [])
    storage.add_link(1, "https://t.me/ch2", ["py"], [])
    links = storage.get_links(1)
    assert len(links) == 2  # noqa: PLR2004


def test_get_all_tracked_links(storage: InMemoryStorage) -> None:
    storage.register_chat(1)
    storage.register_chat(2)
    storage.add_link(1, "https://t.me/shared", [], [])
    storage.add_link(2, "https://t.me/shared", [], [])
    storage.add_link(1, "https://t.me/only1", [], [])

    tracked = storage.get_all_tracked_links()
    assert set(tracked["https://t.me/shared"]) == {1, 2}
    assert tracked["https://t.me/only1"] == [1]
