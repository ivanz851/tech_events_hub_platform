from abc import ABC, abstractmethod
from uuid import UUID

from src.scrapper.models import (
    EventData,
    LinkRecord,
    RouteInfo,
    SubscriptionFilters,
    TrackedLink,
    UserProfile,
)

__all__ = ("AbstractLinkRepository",)


class AbstractLinkRepository(ABC):
    @abstractmethod
    async def register_chat(self, chat_id: int) -> bool: ...

    @abstractmethod
    async def delete_chat(self, chat_id: int) -> bool: ...

    @abstractmethod
    async def chat_exists(self, chat_id: int) -> bool: ...

    @abstractmethod
    async def get_or_create_by_telegram(self, chat_id: int) -> UUID: ...

    @abstractmethod
    async def get_or_create_by_yandex(self, yandex_id: str, email: str | None) -> UUID: ...

    @abstractmethod
    async def link_telegram_to_user(self, user_id: UUID, chat_id: int) -> None: ...

    @abstractmethod
    async def get_links(self, user_id: UUID) -> list[LinkRecord]: ...

    @abstractmethod
    async def add_link(
        self,
        user_id: UUID,
        url: str,
        filters: SubscriptionFilters | None = None,
    ) -> LinkRecord | None: ...

    @abstractmethod
    async def remove_link(self, user_id: UUID, url: str) -> LinkRecord | None: ...

    @abstractmethod
    async def get_tracked_links_page(self, offset: int, limit: int) -> list[TrackedLink]: ...

    @abstractmethod
    async def save_event_data(self, link_id: int, event: EventData) -> None: ...

    @abstractmethod
    async def get_notification_routes(self, user_ids: list[UUID]) -> list[RouteInfo]: ...

    @abstractmethod
    async def update_user_settings(
        self,
        user_id: UUID,
        notify_email: bool | None = None,
        notify_telegram: bool | None = None,
    ) -> None: ...

    @abstractmethod
    async def get_profile(self, user_id: UUID) -> UserProfile | None: ...
