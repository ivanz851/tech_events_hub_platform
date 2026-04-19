from __future__ import annotations
import uuid
from uuid import UUID

from src.scrapper.models import (
    EventData,
    LinkRecord,
    RouteInfo,
    SubscriberDTO,
    SubscriptionFilters,
    TrackedLink,
    UserProfile,
)
from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("InMemoryLinkRepository",)


class InMemoryLinkRepository(AbstractLinkRepository):
    def __init__(self) -> None:
        self._telegram_to_user: dict[int, UUID] = {}
        self._yandex_to_user: dict[str, UUID] = {}
        self._user_to_telegram: dict[UUID, int] = {}
        self._user_to_yandex: dict[UUID, str] = {}
        self._user_emails: dict[UUID, str | None] = {}
        self._user_settings: dict[UUID, dict[str, bool]] = {}
        self._links: dict[UUID, dict[str, LinkRecord]] = {}
        self._next_id: int = 1

    def _create_user(self) -> UUID:
        user_id = uuid.uuid4()
        self._links[user_id] = {}
        return user_id

    async def register_chat(self, chat_id: int) -> bool:
        if chat_id in self._telegram_to_user:
            return False
        user_id = self._create_user()
        self._telegram_to_user[chat_id] = user_id
        self._user_to_telegram[user_id] = chat_id
        return True

    async def delete_chat(self, chat_id: int) -> bool:
        user_id = self._telegram_to_user.pop(chat_id, None)
        if user_id is None:
            return False
        self._user_to_telegram.pop(user_id, None)
        self._links.pop(user_id, None)
        self._user_emails.pop(user_id, None)
        self._user_settings.pop(user_id, None)
        self._yandex_to_user = {k: v for k, v in self._yandex_to_user.items() if v != user_id}
        self._user_to_yandex.pop(user_id, None)
        return True

    async def chat_exists(self, chat_id: int) -> bool:
        return chat_id in self._telegram_to_user

    async def get_or_create_by_telegram(self, chat_id: int) -> UUID:
        if chat_id not in self._telegram_to_user:
            user_id = self._create_user()
            self._telegram_to_user[chat_id] = user_id
            self._user_to_telegram[user_id] = chat_id
        return self._telegram_to_user[chat_id]

    async def get_or_create_by_yandex(
        self,
        yandex_id: str,
        email: str | None,
    ) -> UUID:
        if yandex_id not in self._yandex_to_user:
            user_id = self._create_user()
            self._yandex_to_user[yandex_id] = user_id
            self._user_to_yandex[user_id] = yandex_id
            self._user_emails[user_id] = email
        return self._yandex_to_user[yandex_id]

    async def link_telegram_to_user(self, user_id: UUID, chat_id: int) -> None:
        self._telegram_to_user[chat_id] = user_id
        self._user_to_telegram[user_id] = chat_id
        if user_id not in self._links:
            self._links[user_id] = {}

    async def get_links(self, user_id: UUID) -> list[LinkRecord]:
        return list(self._links.get(user_id, {}).values())

    async def add_link(
        self,
        user_id: UUID,
        url: str,
        filters: SubscriptionFilters | None = None,
    ) -> LinkRecord | None:
        user_links = self._links.get(user_id)
        if user_links is None:
            return None
        if url in user_links:
            return None
        record = LinkRecord(id=self._next_id, url=url, filters=filters)
        self._next_id += 1
        user_links[url] = record
        return record

    async def remove_link(self, user_id: UUID, url: str) -> LinkRecord | None:
        user_links = self._links.get(user_id)
        if user_links is None:
            return None
        return user_links.pop(url, None)

    async def get_tracked_links_page(self, offset: int, limit: int) -> list[TrackedLink]:
        url_to_id: dict[str, int] = {}
        url_to_subscribers: dict[str, list[SubscriberDTO]] = {}

        for user_id, links in self._links.items():
            for url, record in links.items():
                url_to_id[url] = record.id
                url_to_subscribers.setdefault(url, []).append(
                    SubscriberDTO(
                        user_id=user_id,
                        filters=record.filters,
                    ),
                )

        all_entries = [
            TrackedLink(link_id=url_to_id[url], url=url, subscribers=subs)
            for url, subs in sorted(url_to_subscribers.items())
        ]
        return all_entries[offset : offset + limit]

    async def save_event_data(self, link_id: int, event: EventData) -> None:
        pass

    async def get_notification_routes(self, user_ids: list[UUID]) -> list[RouteInfo]:
        result = []
        for uid in user_ids:
            tg_chat_id = self._user_to_telegram.get(uid)
            email = self._user_emails.get(uid)
            settings = self._user_settings.get(uid, {})
            result.append(
                RouteInfo(
                    user_id=uid,
                    tg_chat_id=tg_chat_id,
                    email=email,
                    notify_telegram=settings.get("notify_telegram", True),
                    notify_email=settings.get("notify_email", False),
                ),
            )
        return result

    async def update_user_settings(
        self,
        user_id: UUID,
        notify_email: bool | None = None,
        notify_telegram: bool | None = None,
    ) -> None:
        settings = self._user_settings.setdefault(
            user_id,
            {"notify_telegram": True, "notify_email": False},
        )
        if notify_email is not None:
            settings["notify_email"] = notify_email
        if notify_telegram is not None:
            settings["notify_telegram"] = notify_telegram

    async def get_profile(self, user_id: UUID) -> UserProfile | None:
        if user_id not in self._links:
            return None
        providers: list[str] = []
        if user_id in self._user_to_telegram:
            providers.append("telegram")
        if user_id in self._user_to_yandex:
            providers.append("yandex")
        email = self._user_emails.get(user_id)
        settings = self._user_settings.get(user_id, {})
        return UserProfile(
            user_id=user_id,
            email=email,
            providers=providers,
            notify_telegram=settings.get("notify_telegram", True),
            notify_email=settings.get("notify_email", False),
        )
