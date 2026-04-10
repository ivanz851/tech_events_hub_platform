from src.scrapper.models import EventData, LinkRecord, TrackedLink
from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("InMemoryLinkRepository",)


class InMemoryLinkRepository(AbstractLinkRepository):
    def __init__(self) -> None:
        self._chats: set[int] = set()
        self._links: dict[int, dict[str, LinkRecord]] = {}
        self._next_id: int = 1

    async def register_chat(self, chat_id: int) -> bool:
        if chat_id in self._chats:
            return False
        self._chats.add(chat_id)
        self._links[chat_id] = {}
        return True

    async def delete_chat(self, chat_id: int) -> bool:
        if chat_id not in self._chats:
            return False
        self._chats.discard(chat_id)
        self._links.pop(chat_id, None)
        return True

    async def chat_exists(self, chat_id: int) -> bool:
        return chat_id in self._chats

    async def get_links(self, chat_id: int) -> list[LinkRecord]:
        return list(self._links.get(chat_id, {}).values())

    async def add_link(
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

    async def remove_link(self, chat_id: int, url: str) -> LinkRecord | None:
        chat_links = self._links.get(chat_id)
        if chat_links is None:
            return None
        return chat_links.pop(url, None)

    async def get_tracked_links_page(self, offset: int, limit: int) -> list[TrackedLink]:
        url_to_chats: dict[str, list[int]] = {}
        for chat_id, links in self._links.items():
            for url in links:
                url_to_chats.setdefault(url, []).append(chat_id)

        all_entries = [
            TrackedLink(link_id=idx + 1, url=url, chat_ids=chat_ids)
            for idx, (url, chat_ids) in enumerate(sorted(url_to_chats.items()))
        ]
        return all_entries[offset : offset + limit]

    async def save_event_data(self, link_id: int, event: EventData) -> None:
        pass
