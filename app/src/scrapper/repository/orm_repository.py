from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from src.scrapper.db.models import EventData as EventDataModel
from src.scrapper.db.models import Link, LinkUserMapping, User, UserIdentity, UserSettings
from src.scrapper.models import (
    EventData,
    LinkRecord,
    SubscriberDTO,
    SubscriptionFilters,
    TrackedLink,
)
from src.scrapper.repository.abstract import AbstractLinkRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = ("OrmLinkRepository",)

_TELEGRAM = "telegram"
_YANDEX = "yandex"


class OrmLinkRepository(AbstractLinkRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def _get_user_id_by_identity(
        self,
        session: AsyncSession,
        provider: str,
        provider_id: str,
    ) -> UUID | None:
        stmt = select(UserIdentity.user_id).where(
            UserIdentity.provider == provider,
            UserIdentity.provider_id == provider_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def _create_user_with_identity(
        self,
        session: AsyncSession,
        provider: str,
        provider_id: str,
        email: str | None = None,
    ) -> UUID:
        user = User(id=uuid.uuid4(), email=email)
        session.add(user)
        await session.flush()
        session.add(
            UserIdentity(
                id=uuid.uuid4(),
                user_id=user.id,
                provider=provider,
                provider_id=provider_id,
            ),
        )
        session.add(UserSettings(user_id=user.id))
        await session.commit()
        return user.id  # type: ignore[return-value]

    async def register_chat(self, chat_id: int) -> bool:
        async with self._session_factory() as session:
            existing = await self._get_user_id_by_identity(session, _TELEGRAM, str(chat_id))
            if existing is not None:
                return False
            await self._create_user_with_identity(session, _TELEGRAM, str(chat_id))
            return True

    async def delete_chat(self, chat_id: int) -> bool:
        async with self._session_factory() as session:
            user_id = await self._get_user_id_by_identity(session, _TELEGRAM, str(chat_id))
            if user_id is None:
                return False
            user = await session.get(User, user_id)
            if user is not None:
                await session.delete(user)
                await session.commit()
            return True

    async def chat_exists(self, chat_id: int) -> bool:
        async with self._session_factory() as session:
            return (
                await self._get_user_id_by_identity(session, _TELEGRAM, str(chat_id))
            ) is not None

    async def get_or_create_by_telegram(self, chat_id: int) -> UUID:
        async with self._session_factory() as session:
            existing = await self._get_user_id_by_identity(session, _TELEGRAM, str(chat_id))
            if existing is not None:
                return existing
            return await self._create_user_with_identity(session, _TELEGRAM, str(chat_id))

    async def get_or_create_by_yandex(self, yandex_id: str, email: str | None) -> UUID:
        async with self._session_factory() as session:
            existing = await self._get_user_id_by_identity(session, _YANDEX, yandex_id)
            if existing is not None:
                return existing
            return await self._create_user_with_identity(session, _YANDEX, yandex_id, email)

    async def link_telegram_to_user(self, user_id: UUID, chat_id: int) -> None:
        async with self._session_factory() as session:
            stmt = insert(UserIdentity).values(
                id=uuid.uuid4(),
                user_id=user_id,
                provider=_TELEGRAM,
                provider_id=str(chat_id),
            )
            await session.execute(stmt)
            await session.commit()

    async def get_links(self, user_id: UUID) -> list[LinkRecord]:
        async with self._session_factory() as session:
            stmt = (
                select(Link, LinkUserMapping)
                .join(LinkUserMapping, LinkUserMapping.link_id == Link.id)
                .where(LinkUserMapping.user_id == user_id)
                .order_by(Link.id)
            )
            rows = (await session.execute(stmt)).all()
            return [
                LinkRecord(
                    id=int(link.id),  # type: ignore[arg-type]
                    url=str(link.url),
                    filters=_parse_filters(mapping.filters),
                )
                for link, mapping in rows
            ]

    async def add_link(
        self,
        user_id: UUID,
        url: str,
        filters: SubscriptionFilters | None = None,
    ) -> LinkRecord | None:
        async with self._session_factory() as session:
            stmt = insert(Link).values(url=url).on_conflict_do_nothing(index_elements=["url"])
            await session.execute(stmt)
            await session.flush()

            link_id_row = await session.execute(select(Link.id).where(Link.url == url))
            link_id = link_id_row.scalar_one()

            existing = await session.get(LinkUserMapping, {"link_id": link_id, "user_id": user_id})
            if existing is not None:
                return None

            filters_dict = filters.model_dump(mode="json", exclude_none=True) if filters else {}
            mapping = LinkUserMapping(link_id=link_id, user_id=user_id, filters=filters_dict)
            session.add(mapping)
            await session.commit()
            return LinkRecord(id=int(link_id), url=url, filters=filters)

    async def remove_link(self, user_id: UUID, url: str) -> LinkRecord | None:
        async with self._session_factory() as session:
            link_row = await session.execute(select(Link).where(Link.url == url))
            link = link_row.scalar_one_or_none()
            if link is None:
                return None

            mapping = await session.get(
                LinkUserMapping,
                {"link_id": link.id, "user_id": user_id},
            )
            if mapping is None:
                return None

            record = LinkRecord(
                id=int(link.id),  # type: ignore[arg-type]
                url=str(link.url),
                filters=_parse_filters(mapping.filters),
            )
            await session.delete(mapping)
            await session.commit()
            return record

    async def get_tracked_links_page(self, offset: int, limit: int) -> list[TrackedLink]:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT
                    l.id,
                    l.url,
                    jsonb_agg(jsonb_build_object(
                        'user_id', lum.user_id,
                        'chat_id', ui.provider_id,
                        'filters', lum.filters
                    )) AS subscribers
                FROM link l
                JOIN link_user_mapping lum ON l.id = lum.link_id
                LEFT JOIN user_identities ui
                    ON ui.user_id = lum.user_id AND ui.provider = 'telegram'
                GROUP BY l.id, l.url
                ORDER BY l.id
                LIMIT :limit OFFSET :offset
                """,
            )
            rows = (await session.execute(stmt, {"limit": limit, "offset": offset})).all()
            return [_parse_tracked_link(r) for r in rows]

    async def save_event_data(self, link_id: int, event: EventData) -> None:
        async with self._session_factory() as session:
            record = EventDataModel(
                link_id=link_id,
                title=event.title,
                event_date=event.event_date,
                location=event.location,
                price=event.price,
                registration_url=event.registration_url,
                format=event.format,
                event_type=event.event_type,
                summary=event.summary,
                tags=event.tags,
                organizer=event.organizer,
            )
            session.add(record)
            await session.commit()


def _parse_filters(raw: dict[str, Any] | None) -> SubscriptionFilters | None:
    if not raw:
        return None
    return SubscriptionFilters.model_validate(raw)


def _parse_tracked_link(row: Any) -> TrackedLink:  # noqa: ANN401
    link_id = int(row[0])
    url = str(row[1])
    raw_subscribers: list[dict[str, Any]] = row[2] or []
    subscribers = [
        SubscriberDTO(
            user_id=UUID(str(sub["user_id"])),
            tg_chat_id=int(sub["chat_id"]) if sub.get("chat_id") is not None else None,
            filters=_parse_filters(sub.get("filters")),
        )
        for sub in raw_subscribers
    ]
    return TrackedLink(link_id=link_id, url=url, subscribers=subscribers)
