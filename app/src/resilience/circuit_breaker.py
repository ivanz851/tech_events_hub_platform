from __future__ import annotations
import time
from collections import deque
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

__all__ = ("CircuitBreaker", "CircuitBreakerOpenError")

_T = TypeVar("_T")


class CircuitBreakerOpenError(Exception):
    pass


class _State(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(
        self,
        sliding_window_size: int = 1,
        min_calls: int = 1,
        failure_rate_threshold: float = 100.0,
        wait_duration_seconds: float = 1.0,
        permitted_calls_in_half_open: int = 1,
    ) -> None:
        self._window_size = sliding_window_size
        self._min_calls = min_calls
        self._threshold = failure_rate_threshold
        self._wait = wait_duration_seconds
        self._permitted_half_open = permitted_calls_in_half_open
        self._state = _State.CLOSED
        self._results: deque[bool] = deque(maxlen=sliding_window_size)
        self._opened_at: float = 0.0
        self._half_open_attempts = 0

    @property
    def state(self) -> str:
        return self._state.value

    async def call(self, fn: Callable[[], Coroutine[Any, Any, _T]]) -> _T:
        self._check_state()
        try:
            result = await fn()
        except Exception:
            self._record(success=False)
            raise
        else:
            self._record(success=True)
            return result

    def _check_state(self) -> None:
        if self._state == _State.OPEN:
            if time.monotonic() - self._opened_at >= self._wait:
                self._state = _State.HALF_OPEN
                self._half_open_attempts = 0
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        if self._state == _State.HALF_OPEN:
            if self._half_open_attempts >= self._permitted_half_open:
                raise CircuitBreakerOpenError("Circuit breaker is HALF_OPEN: call limit reached")
            self._half_open_attempts += 1

    def _record(self, success: bool) -> None:
        self._results.append(not success)
        if self._state == _State.HALF_OPEN:
            if success:
                self._state = _State.CLOSED
                self._results.clear()
            else:
                self._state = _State.OPEN
                self._opened_at = time.monotonic()
            return
        if self._should_open():
            self._state = _State.OPEN
            self._opened_at = time.monotonic()

    def _should_open(self) -> bool:
        if len(self._results) < self._min_calls:
            return False
        failures = sum(1 for r in self._results if r)
        return (failures / len(self._results)) * 100.0 >= self._threshold
