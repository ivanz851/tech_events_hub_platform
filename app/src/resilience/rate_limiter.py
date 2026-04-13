from __future__ import annotations
import time
from collections import defaultdict, deque
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.types import ASGIApp

__all__ = ("RateLimitMiddleware",)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, requests_per_minute: int) -> None:
        super().__init__(app)
        self._limit = requests_per_minute
        self._window = 60.0
        self._counters: defaultdict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        timestamps = self._counters[ip]
        cutoff = now - self._window
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()
        if len(timestamps) >= self._limit:
            return JSONResponse(status_code=429, content={"error": "Too Many Requests"})
        timestamps.append(now)
        return await call_next(request)
