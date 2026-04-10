import psycopg

from src.scrapper.models import EventData, LinkRecord, TrackedLink
from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("SqlLinkRepository",)


class SqlLinkRepository(AbstractLinkRepository):
    def __init__(self, db_dsn: str) -> None:
        self._dsn = db_dsn

    async def register_chat(self, chat_id: int) -> bool:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute("SELECT id FROM tg_chat WHERE id = %s", (chat_id,))
            if await cur.fetchone() is not None:
                return False
            await cur.execute("INSERT INTO tg_chat(id) VALUES (%s)", (chat_id,))
            await conn.commit()
            return True

    async def delete_chat(self, chat_id: int) -> bool:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute("SELECT id FROM tg_chat WHERE id = %s", (chat_id,))
            if await cur.fetchone() is None:
                return False
            await cur.execute("DELETE FROM tg_chat WHERE id = %s", (chat_id,))
            await conn.commit()
            return True

    async def chat_exists(self, chat_id: int) -> bool:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM tg_chat WHERE id = %s", (chat_id,))
            return await cur.fetchone() is not None

    async def get_links(self, chat_id: int) -> list[LinkRecord]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT l.id, l.url, lum.tags, lum.filters
                FROM link l
                JOIN link_user_mapping lum ON l.id = lum.link_id
                WHERE lum.chat_id = %s
                ORDER BY l.id
                """,
                (chat_id,),
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
        chat_id: int,
        url: str,
        tags: list[str],
        filters: list[str],
    ) -> LinkRecord | None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM tg_chat WHERE id = %s", (chat_id,))
            if await cur.fetchone() is None:
                return None

            await cur.execute(
                "INSERT INTO link(url) VALUES (%s) ON CONFLICT (url) DO NOTHING",
                (url,),
            )
            await cur.execute("SELECT id FROM link WHERE url = %s", (url,))
            link_id: int = (await cur.fetchone())[0]  # type: ignore[index]

            await cur.execute(
                "SELECT 1 FROM link_user_mapping WHERE link_id = %s AND chat_id = %s",
                (link_id, chat_id),
            )
            if await cur.fetchone() is not None:
                return None

            await cur.execute(
                "INSERT INTO link_user_mapping(link_id, chat_id, tags, filters) "
                "VALUES (%s, %s, %s, %s)",
                (link_id, chat_id, tags, filters),
            )
            await conn.commit()
            return LinkRecord(id=link_id, url=url, tags=tags, filters=filters)

    async def remove_link(self, chat_id: int, url: str) -> LinkRecord | None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute("SELECT id FROM link WHERE url = %s", (url,))
            row = await cur.fetchone()
            if row is None:
                return None
            link_id: int = row[0]

            await cur.execute(
                "SELECT tags, filters FROM link_user_mapping "
                "WHERE link_id = %s AND chat_id = %s",
                (link_id, chat_id),
            )
            mapping = await cur.fetchone()
            if mapping is None:
                return None

            await cur.execute(
                "DELETE FROM link_user_mapping WHERE link_id = %s AND chat_id = %s",
                (link_id, chat_id),
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
                SELECT l.id, l.url, array_agg(lum.chat_id)
                FROM link l
                JOIN link_user_mapping lum ON l.id = lum.link_id
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
