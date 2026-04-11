from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import redis.asyncio

__all__ = ("NotifyModeStore",)

_IMMEDIATE = "immediate"
_DIGEST = "digest"
_VALID_MODES = frozenset({_IMMEDIATE, _DIGEST})


class NotifyModeStore:
    def __init__(self, redis_client: redis.asyncio.Redis) -> None:
        self._redis = redis_client

    async def get(self, chat_id: int) -> str:
        raw: Any = await self._redis.get(f"notify_mode:{chat_id}")
        return str(raw) if raw in _VALID_MODES else _IMMEDIATE

    async def set(self, chat_id: int, mode: str) -> None:
        await self._redis.set(f"notify_mode:{chat_id}", mode)
