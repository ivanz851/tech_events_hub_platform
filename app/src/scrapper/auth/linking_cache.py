from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID

__all__ = ("AbstractLinkingCache", "InMemoryLinkingCache", "RedisLinkingCache")


class AbstractLinkingCache(ABC):
    @abstractmethod
    async def save_link_token(self, token: str, user_id: UUID, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def get_user_id_by_token(self, token: str) -> UUID | None: ...

    @abstractmethod
    async def delete_token(self, token: str) -> None: ...


class InMemoryLinkingCache(AbstractLinkingCache):
    def __init__(self) -> None:
        self._store: dict[str, UUID] = {}

    async def save_link_token(
        self,
        token: str,
        user_id: UUID,
        ttl_seconds: int,  # noqa: ARG002
    ) -> None:
        self._store[token] = user_id

    async def get_user_id_by_token(self, token: str) -> UUID | None:
        return self._store.get(token)

    async def delete_token(self, token: str) -> None:
        self._store.pop(token, None)


class RedisLinkingCache(AbstractLinkingCache):
    _PREFIX = "tg_link:"

    def __init__(self, redis_client: object) -> None:
        self._redis = redis_client

    async def save_link_token(self, token: str, user_id: UUID, ttl_seconds: int) -> None:
        await self._redis.set(  # type: ignore[attr-defined]
            f"{self._PREFIX}{token}",
            str(user_id),
            ex=ttl_seconds,
        )

    async def get_user_id_by_token(self, token: str) -> UUID | None:
        value = await self._redis.get(f"{self._PREFIX}{token}")  # type: ignore[attr-defined]
        if value is None:
            return None
        raw = value.decode() if isinstance(value, bytes) else str(value)
        return UUID(raw)

    async def delete_token(self, token: str) -> None:
        await self._redis.delete(f"{self._PREFIX}{token}")  # type: ignore[attr-defined]
