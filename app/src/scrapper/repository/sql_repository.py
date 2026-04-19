from __future__ import annotations
import json
import uuid
from typing import Any
from uuid import UUID

import psycopg

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
                SELECT l.id, l.url, lum.filters
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
                    filters=_parse_filters(r[2]),
                )
                for r in rows
            ]

    async def add_link(
        self,
        user_id: UUID,
        url: str,
        filters: SubscriptionFilters | None = None,
    ) -> LinkRecord | None:
        filters_dict = filters.model_dump(mode="json", exclude_none=True) if filters else {}
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
                "INSERT INTO link_user_mapping(link_id, user_id, filters) VALUES (%s, %s, %s)",
                (link_id, str(user_id), json.dumps(filters_dict)),
            )
            await conn.commit()
            return LinkRecord(id=link_id, url=url, filters=filters)

    async def remove_link(self, user_id: UUID, url: str) -> LinkRecord | None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute("SELECT id FROM link WHERE url = %s", (url,))
            row = await cur.fetchone()
            if row is None:
                return None
            link_id: int = row[0]

            await cur.execute(
                "SELECT filters FROM link_user_mapping WHERE link_id = %s AND user_id = %s",
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
            return LinkRecord(id=link_id, url=url, filters=_parse_filters(mapping[0]))

    async def get_tracked_links_page(self, offset: int, limit: int) -> list[TrackedLink]:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    l.id,
                    l.url,
                    jsonb_agg(jsonb_build_object(
                        'user_id', lum.user_id,
                        'filters', lum.filters
                    )) AS subscribers
                FROM link l
                JOIN link_user_mapping lum ON l.id = lum.link_id
                GROUP BY l.id, l.url
                ORDER BY l.id
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = await cur.fetchall()
            return [_parse_tracked_link(r) for r in rows]

    async def get_notification_routes(self, user_ids: list[UUID]) -> list[RouteInfo]:
        if not user_ids:
            return []
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    u.id AS user_id,
                    (SELECT ui.provider_id FROM user_identities ui
                     WHERE ui.user_id = u.id AND ui.provider = 'telegram' LIMIT 1) AS tg_chat_id,
                    u.email,
                    COALESCE(us.notify_telegram, TRUE) AS notify_telegram,
                    COALESCE(us.notify_email, FALSE) AS notify_email
                FROM users u
                LEFT JOIN user_settings us ON us.user_id = u.id
                WHERE u.id = ANY(%s)
                """,
                ([str(uid) for uid in user_ids],),
            )
            rows = await cur.fetchall()
            return [
                RouteInfo(
                    user_id=UUID(str(r[0])),
                    tg_chat_id=int(r[1]) if r[1] is not None else None,
                    email=str(r[2]) if r[2] is not None else None,
                    notify_telegram=bool(r[3]),
                    notify_email=bool(r[4]),
                )
                for r in rows
            ]

    async def update_user_settings(
        self,
        user_id: UUID,
        notify_email: bool | None = None,
        notify_telegram: bool | None = None,
    ) -> None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_settings(user_id, notify_email, notify_telegram)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    notify_email = COALESCE(EXCLUDED.notify_email, user_settings.notify_email),
                    notify_telegram = COALESCE(
                        EXCLUDED.notify_telegram, user_settings.notify_telegram
                    )
                """,
                (str(user_id), notify_email, notify_telegram),
            )
            await conn.commit()

    async def get_profile(self, user_id: UUID) -> UserProfile | None:
        async with await psycopg.AsyncConnection.connect(self._dsn) as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT id, email FROM users WHERE id = %s",
                (str(user_id),),
            )
            user_row = await cur.fetchone()
            if user_row is None:
                return None
            await cur.execute(
                "SELECT DISTINCT provider FROM user_identities WHERE user_id = %s",
                (str(user_id),),
            )
            providers = [str(r[0]) for r in await cur.fetchall()]
            await cur.execute(
                "SELECT notify_telegram, notify_email FROM user_settings WHERE user_id = %s",
                (str(user_id),),
            )
            settings_row = await cur.fetchone()
            return UserProfile(
                user_id=user_id,
                email=str(user_row[1]) if user_row[1] is not None else None,
                providers=providers,
                notify_telegram=bool(settings_row[0]) if settings_row else True,
                notify_email=bool(settings_row[1]) if settings_row else False,
            )

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


def _parse_filters(raw: Any) -> SubscriptionFilters | None:  # noqa: ANN401
    if not raw:
        return None
    if isinstance(raw, str):
        raw = json.loads(raw)
    return SubscriptionFilters.model_validate(raw) if raw else None


def _parse_tracked_link(row: Any) -> TrackedLink:  # noqa: ANN401
    link_id = int(row[0])
    url = str(row[1])
    raw_subscribers: list[dict[str, Any]] = row[2] or []
    subscribers = [
        SubscriberDTO(
            user_id=UUID(str(sub["user_id"])),
            filters=_parse_filters(sub.get("filters")),
        )
        for sub in raw_subscribers
    ]
    return TrackedLink(link_id=link_id, url=url, subscribers=subscribers)
