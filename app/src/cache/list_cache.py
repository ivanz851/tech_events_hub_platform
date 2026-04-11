from __future__ import annotations
import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from src.clients.scrapper import LinkResponse

if TYPE_CHECKING:
    import redis.asyncio

__all__ = ("ListCache",)

_TTL_SECONDS = 300


class ListCache:
    def __init__(self, redis_client: redis.asyncio.Redis) -> None:
        self._redis = redis_client

    async def get(self, chat_id: int) -> list[LinkResponse] | None:
        raw: Any = await self._redis.get(f"list:{chat_id}")
        if raw is None:
            return None
        data: list[dict[str, Any]] = json.loads(raw)
        return [LinkResponse(**item) for item in data]

    async def set(self, chat_id: int, links: list[LinkResponse]) -> None:
        serialized = json.dumps([asdict(link) for link in links])
        await self._redis.setex(f"list:{chat_id}", _TTL_SECONDS, serialized)

    async def invalidate(self, chat_id: int) -> None:
        await self._redis.delete(f"list:{chat_id}")
