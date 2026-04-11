from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import redis.asyncio

__all__ = ("DigestStore",)

_USERS_KEY = "digest_users"


class DigestStore:
    def __init__(self, redis_client: redis.asyncio.Redis) -> None:
        self._redis = redis_client

    async def add(self, chat_id: int, message: str) -> None:
        await self._redis.rpush(f"digest:{chat_id}", message)  # type: ignore[misc]
        await self._redis.sadd(_USERS_KEY, str(chat_id))  # type: ignore[misc]

    async def get_users(self) -> list[int]:
        members: Any = await self._redis.smembers(_USERS_KEY)  # type: ignore[misc]
        return [int(m) for m in members]

    async def get_all(self, chat_id: int) -> list[str]:
        result: Any = await self._redis.lrange(f"digest:{chat_id}", 0, -1)  # type: ignore[misc]
        return list(result)

    async def clear(self, chat_id: int) -> None:
        await self._redis.delete(f"digest:{chat_id}")
        await self._redis.srem(_USERS_KEY, str(chat_id))  # type: ignore[misc]
