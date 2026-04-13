from __future__ import annotations
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeVar

import httpx

from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.resilience.retry import with_retry

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

__all__ = ("BotClient", "BotClientError")

_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class BotClientError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class BotClient:
    def __init__(
        self,
        base_url: str = "http://localhost:7777/api/v1",
        timeout_seconds: float = 5.0,
        retry_count: int = 3,
        retry_backoff_seconds: float = 1.0,
        retry_on_codes: set[int] | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = httpx.Timeout(timeout_seconds)
        self._retry_count = retry_count
        self._retry_backoff = retry_backoff_seconds
        self._retry_codes = retry_on_codes if retry_on_codes is not None else {502, 503, 429}
        self._cb = circuit_breaker

    async def _execute(self, fn: Callable[[], Coroutine[Any, Any, _T]]) -> _T:
        async def _retried() -> _T:
            return await with_retry(
                fn,
                retry_count=self._retry_count,
                backoff_seconds=self._retry_backoff,
                retryable_codes=self._retry_codes,
            )

        try:
            if self._cb is not None:
                return await self._cb.call(_retried)
            return await _retried()
        except CircuitBreakerOpenError as exc:
            raise BotClientError(503, str(exc)) from exc

    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        tg_chat_ids: list[int],
    ) -> None:
        payload = {
            "id": update_id,
            "url": url,
            "description": description,
            "tgChatIds": tg_chat_ids,
        }

        async def _call() -> None:
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout,
                ) as client:
                    resp = await client.post("/updates", json=payload)
                    if resp.status_code != HTTPStatus.OK:
                        raise BotClientError(resp.status_code, resp.text)
            except httpx.RequestError as exc:
                raise BotClientError(0, str(exc)) from exc

        await self._execute(_call)
        logger.info(
            "Sent update to bot",
            extra={"url": url, "chat_count": len(tg_chat_ids)},
        )
