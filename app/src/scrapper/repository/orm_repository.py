from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.scrapper.db.models import EventData as EventDataModel
from src.scrapper.db.models import Link, LinkUserMapping, TgChat
from src.scrapper.models import EventData, LinkRecord, TrackedLink
from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("OrmLinkRepository",)


class OrmLinkRepository(AbstractLinkRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def register_chat(self, chat_id: int) -> bool:
        async with self._session_factory() as session:
            existing = await session.get(TgChat, chat_id)
            if existing is not None:
                return False
            session.add(TgChat(id=chat_id))
            await session.commit()
            return True

    async def delete_chat(self, chat_id: int) -> bool:
        async with self._session_factory() as session:
            existing = await session.get(TgChat, chat_id)
            if existing is None:
                return False
            await session.delete(existing)
            await session.commit()
            return True

    async def chat_exists(self, chat_id: int) -> bool:
        async with self._session_factory() as session:
            return await session.get(TgChat, chat_id) is not None

    async def get_links(self, chat_id: int) -> list[LinkRecord]:
        async with self._session_factory() as session:
            stmt = (
                select(Link, LinkUserMapping)
                .join(LinkUserMapping, LinkUserMapping.link_id == Link.id)
                .where(LinkUserMapping.chat_id == chat_id)
                .order_by(Link.id)
            )
            rows = (await session.execute(stmt)).all()
            return [
                LinkRecord(
                    id=int(link.id),  # type: ignore[arg-type]
                    url=str(link.url),
                    tags=list(mapping.tags or []),
                    filters=list(mapping.filters or []),
                )
                for link, mapping in rows
            ]

    async def add_link(
        self,
        chat_id: int,
        url: str,
        tags: list[str],
        filters: list[str],
    ) -> LinkRecord | None:
        async with self._session_factory() as session:
            if await session.get(TgChat, chat_id) is None:
                return None

            stmt = insert(Link).values(url=url).on_conflict_do_nothing(index_elements=["url"])
            await session.execute(stmt)
            await session.flush()

            link_id_row = await session.execute(select(Link.id).where(Link.url == url))
            link_id = link_id_row.scalar_one()

            existing = await session.get(LinkUserMapping, {"link_id": link_id, "chat_id": chat_id})
            if existing is not None:
                return None

            mapping = LinkUserMapping(
                link_id=link_id,
                chat_id=chat_id,
                tags=tags,
                filters=filters,
            )
            session.add(mapping)
            await session.commit()
            return LinkRecord(id=int(link_id), url=url, tags=tags, filters=filters)

    async def remove_link(self, chat_id: int, url: str) -> LinkRecord | None:
        async with self._session_factory() as session:
            link_row = await session.execute(select(Link).where(Link.url == url))
            link = link_row.scalar_one_or_none()
            if link is None:
                return None

            mapping = await session.get(
                LinkUserMapping,
                {"link_id": link.id, "chat_id": chat_id},
            )
            if mapping is None:
                return None

            record = LinkRecord(
                id=int(link.id),  # type: ignore[arg-type]
                url=str(link.url),
                tags=list(mapping.tags or []),
                filters=list(mapping.filters or []),
            )
            await session.delete(mapping)
            await session.commit()
            return record

    async def get_tracked_links_page(self, offset: int, limit: int) -> list[TrackedLink]:
        async with self._session_factory() as session:
            stmt = (
                select(Link.id, Link.url, func.array_agg(LinkUserMapping.chat_id))
                .join(LinkUserMapping, LinkUserMapping.link_id == Link.id)
                .group_by(Link.id, Link.url)
                .order_by(Link.id)
                .offset(offset)
                .limit(limit)
            )
            rows = (await session.execute(stmt)).all()
            return [
                TrackedLink(link_id=int(r[0]), url=str(r[1]), chat_ids=list(r[2])) for r in rows
            ]

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
