from __future__ import annotations
import asyncio
import logging
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

__all__ = ("with_retry",)

_T = TypeVar("_T")

logger = logging.getLogger(__name__)


async def with_retry(
    fn: Callable[[], Coroutine[Any, Any, _T]],
    retry_count: int,
    backoff_seconds: float,
    retryable_codes: set[int],
) -> _T:
    last_exc: BaseException | None = None
    for attempt in range(retry_count + 1):
        try:
            return await fn()
        except Exception as exc:  # noqa: PERF203
            code: int | None = getattr(exc, "status_code", None)
            if code not in retryable_codes:
                raise
            last_exc = exc
            if attempt < retry_count:
                logger.warning(
                    "Retrying request",
                    extra={"attempt": attempt + 1, "status_code": code},
                )
                await asyncio.sleep(backoff_seconds)
    raise last_exc  # type: ignore[misc]
