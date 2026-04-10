from abc import ABC, abstractmethod

from src.scrapper.models import EventData, LinkRecord, TrackedLink

__all__ = ("AbstractLinkRepository",)


class AbstractLinkRepository(ABC):
    @abstractmethod
    async def register_chat(self, chat_id: int) -> bool: ...

    @abstractmethod
    async def delete_chat(self, chat_id: int) -> bool: ...

    @abstractmethod
    async def chat_exists(self, chat_id: int) -> bool: ...

    @abstractmethod
    async def get_links(self, chat_id: int) -> list[LinkRecord]: ...

    @abstractmethod
    async def add_link(
        self,
        chat_id: int,
        url: str,
        tags: list[str],
        filters: list[str],
    ) -> LinkRecord | None: ...

    @abstractmethod
    async def remove_link(self, chat_id: int, url: str) -> LinkRecord | None: ...

    @abstractmethod
    async def get_tracked_links_page(self, offset: int, limit: int) -> list[TrackedLink]: ...

    @abstractmethod
    async def save_event_data(self, link_id: int, event: EventData) -> None: ...
