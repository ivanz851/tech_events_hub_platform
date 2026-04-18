import uuid
from uuid import UUID

import psycopg

from src.scrapper.models import EventData, LinkRecord, TrackedLink
from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("SqlLinkRepository",)

_TELEGRAM = "telegram"
_YANDEX = "yandex"


class SqlLinkRepository(AbstractLinkRepository):
    def __init__(self, db_dsn: str) -> None:
        self._dsn = db_dsn

    async def _get_user_id_by_identity(
        self,
        cur: psycopg.AsyncCursor[tuple[object, ...]],  # type: ignore[type-arg]
        provider: str,
        provider_id: str,
    ) -> UUID | None:
        await cur.execute(
            "SELECT user_id FROM user_identities WHERE provider = %s AND provider_id = %s",
            (provider, provider_id),
        )
        row = await cur.fetchone()
        return UUID(str(row[0])) if row else None

    async def _create_user_with_identity(
        self,
        conn: psycopg.AsyncConnection[tuple[object, ...]],  # type: ignore[type-arg]
        provider: str,
        provider_id: str,
        email: str | None = None,
    ) -> UUID:
        user_id = uuid.uuid4()
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users(id, email) VALUES (%s, %s)",
                (str(user_id), email),
            )
            await cur.execute(
                "INSERT INTO user_identities(id, user_id, provider, provider_id) "
                "VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), str(user_id), provider, provider_id),
            )
            await cur.execute(
                "INSERT INTO user_settings(user_id) VALUES (%s)",
                (str(user_id),),
            )
        await conn.commit()
        return user_id

    async def register_chat(self, chat_id: int) -> bool:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                existing = await self._get_user_id_by_identity(cur, _TELEGRAM, str(chat_id))
                if existing is not None:
                    return False
            await self._create_user_with_identity(conn, _TELEGRAM, str(chat_id))
            return True

    async def delete_chat(self, chat_id: int) -> bool:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                user_id = await self._get_user_id_by_identity(cur, _TELEGRAM, str(chat_id))
                if user_id is None:
                    return False
                await cur.execute("DELETE FROM users WHERE id = %s", (str(user_id),))
            await conn.commit()
            return True

    async def chat_exists(self, chat_id: int) -> bool:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            return (await self._get_user_id_by_identity(cur, _TELEGRAM, str(chat_id))) is not None

    async def get_or_create_by_telegram(self, chat_id: int) -> UUID:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                existing = await self._get_user_id_by_identity(cur, _TELEGRAM, str(chat_id))
                if existing is not None:
                    return existing
            return await self._create_user_with_identity(conn, _TELEGRAM, str(chat_id))

    async def get_or_create_by_yandex(self, yandex_id: str, email: str | None) -> UUID:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                existing = await self._get_user_id_by_identity(cur, _YANDEX, yandex_id)
                if existing is not None:
                    return existing
            return await self._create_user_with_identity(conn, _YANDEX, yandex_id, email)

    async def link_telegram_to_user(self, user_id: UUID, chat_id: int) -> None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO user_identities(id, user_id, provider, provider_id) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (provider, provider_id) DO NOTHING",
                (str(uuid.uuid4()), str(user_id), _TELEGRAM, str(chat_id)),
            )
            await conn.commit()

    async def get_links(self, user_id: UUID) -> list[LinkRecord]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT l.id, l.url, lum.tags, lum.filters
                FROM link l
                JOIN link_user_mapping lum ON l.id = lum.link_id
                WHERE lum.user_id = %s
                ORDER BY l.id
                """,
                (str(user_id),),
            )
            rows = await cur.fetchall()
            return [
                LinkRecord(
                    id=r[0],
                    url=r[1],
                    tags=list(r[2] or []),
                    filters=list(r[3] or []),
                )
                for r in rows
            ]

    async def add_link(
        self,
        user_id: UUID,
        url: str,
        tags: list[str],
        filters: list[str],
    ) -> LinkRecord | None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO link(url) VALUES (%s) ON CONFLICT (url) DO NOTHING",
                (url,),
            )
            await cur.execute("SELECT id FROM link WHERE url = %s", (url,))
            link_row = await cur.fetchone()
            link_id: int = link_row[0]  # type: ignore[index]

            await cur.execute(
                "SELECT 1 FROM link_user_mapping WHERE link_id = %s AND user_id = %s",
                (link_id, str(user_id)),
            )
            if await cur.fetchone() is not None:
                return None

            await cur.execute(
                "INSERT INTO link_user_mapping(link_id, user_id, tags, filters) "
                "VALUES (%s, %s, %s, %s)",
                (link_id, str(user_id), tags, filters),
            )
            await conn.commit()
            return LinkRecord(id=link_id, url=url, tags=tags, filters=filters)

    async def remove_link(self, user_id: UUID, url: str) -> LinkRecord | None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute("SELECT id FROM link WHERE url = %s", (url,))
            row = await cur.fetchone()
            if row is None:
                return None
            link_id: int = row[0]

            await cur.execute(
                "SELECT tags, filters FROM link_user_mapping "
                "WHERE link_id = %s AND user_id = %s",
                (link_id, str(user_id)),
            )
            mapping = await cur.fetchone()
            if mapping is None:
                return None

            await cur.execute(
                "DELETE FROM link_user_mapping WHERE link_id = %s AND user_id = %s",
                (link_id, str(user_id)),
            )
            await conn.commit()
            return LinkRecord(
                id=link_id,
                url=url,
                tags=list(mapping[0] or []),
                filters=list(mapping[1] or []),
            )

    async def get_tracked_links_page(self, offset: int, limit: int) -> list[TrackedLink]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT l.id, l.url, array_agg(ui.provider_id::bigint)
                FROM link l
                JOIN link_user_mapping lum ON l.id = lum.link_id
                JOIN user_identities ui
                  ON ui.user_id = lum.user_id AND ui.provider = 'telegram'
                GROUP BY l.id, l.url
                ORDER BY l.id
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = await cur.fetchall()
            return [TrackedLink(link_id=r[0], url=r[1], chat_ids=list(r[2])) for r in rows]

    async def save_event_data(self, link_id: int, event: EventData) -> None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO event_data("
                "link_id, title, event_date, location, price, "
                "registration_url, format, event_type, summary, tags, organizer"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    link_id,
                    event.title,
                    event.event_date,
                    event.location,
                    event.price,
                    event.registration_url,
                    event.format,
                    event.event_type,
                    event.summary,
                    event.tags,
                    event.organizer,
                ),
            )
            await conn.commit()
