import time
from dataclasses import dataclass, field

__all__ = ("LinkRecord", "InMemoryStorage")


@dataclass
class LinkRecord:
    id: int
    url: str
    tags: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    added_at: float = field(default_factory=time.time)


class InMemoryStorage:
    def __init__(self) -> None:
        self._chats: set[int] = set()
        self._links: dict[int, dict[str, LinkRecord]] = {}
        self._next_id: int = 1

    def register_chat(self, chat_id: int) -> bool:
        if chat_id in self._chats:
            return False
        self._chats.add(chat_id)
        self._links[chat_id] = {}
        return True

    def delete_chat(self, chat_id: int) -> bool:
        if chat_id not in self._chats:
            return False
        self._chats.discard(chat_id)
        self._links.pop(chat_id, None)
        return True

    def chat_exists(self, chat_id: int) -> bool:
        return chat_id in self._chats

    def get_links(self, chat_id: int) -> list[LinkRecord]:
        return list(self._links.get(chat_id, {}).values())

    def add_link(
        self,
        chat_id: int,
        url: str,
        tags: list[str],
        filters: list[str],
    ) -> LinkRecord | None:
        chat_links = self._links.get(chat_id)
        if chat_links is None:
            return None
        if url in chat_links:
            return None
        record = LinkRecord(id=self._next_id, url=url, tags=tags, filters=filters)
        self._next_id += 1
        chat_links[url] = record
        return record

    def remove_link(self, chat_id: int, url: str) -> LinkRecord | None:
        chat_links = self._links.get(chat_id)
        if chat_links is None:
            return None
        return chat_links.pop(url, None)

    def get_all_tracked_links(self) -> dict[str, list[int]]:
        """Returns mapping of url -> list of subscribed chat_ids."""
        result: dict[str, list[int]] = {}
        for chat_id, links in self._links.items():
            for url in links:
                result.setdefault(url, []).append(chat_id)
        return result

    def get_link_updated_at(self, url: str) -> float:
        """Returns the most recent added_at timestamp for a url across all chats."""
        latest = 0.0
        for links in self._links.values():
            if url in links:
                latest = max(latest, links[url].added_at)
        return latest
