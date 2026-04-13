import asyncio
import time

import pytest

from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


def _make_cb(**kwargs: object) -> CircuitBreaker:
    defaults: dict[str, object] = {
        "sliding_window_size": 1,
        "min_calls": 1,
        "failure_rate_threshold": 100.0,
        "wait_duration_seconds": 60.0,
        "permitted_calls_in_half_open": 1,
    }
    defaults.update(kwargs)
    return CircuitBreaker(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_closed_state_allows_calls() -> None:
    cb = _make_cb()

    async def _ok() -> str:
        return "ok"

    result = await cb.call(_ok)
    assert result == "ok"
    assert cb.state == "CLOSED"


@pytest.mark.asyncio
async def test_circuit_opens_after_failure() -> None:
    cb = _make_cb()

    async def _fail() -> None:
        raise RuntimeError("error")

    with pytest.raises(RuntimeError):
        await cb.call(_fail)

    assert cb.state == "OPEN"


@pytest.mark.asyncio
async def test_open_circuit_fails_fast_before_timeout() -> None:
    cb = _make_cb(wait_duration_seconds=60.0)

    async def _fail() -> None:
        raise RuntimeError("error")

    with pytest.raises(RuntimeError):
        await cb.call(_fail)

    assert cb.state == "OPEN"

    async def _slow_failing() -> None:
        await asyncio.sleep(100)
        raise RuntimeError("should not reach")

    start = time.monotonic()
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(_slow_failing)
    elapsed = time.monotonic() - start

    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_half_open_closes_on_success() -> None:
    cb = _make_cb(wait_duration_seconds=0.01)

    async def _fail() -> None:
        raise RuntimeError("error")

    with pytest.raises(RuntimeError):
        await cb.call(_fail)

    assert cb.state == "OPEN"
    await asyncio.sleep(0.02)

    async def _ok() -> str:
        return "ok"

    result = await cb.call(_ok)
    assert result == "ok"
    assert cb.state == "CLOSED"


@pytest.mark.asyncio
async def test_half_open_reopens_on_failure() -> None:
    cb = _make_cb(wait_duration_seconds=0.01)

    async def _fail() -> None:
        raise RuntimeError("error")

    with pytest.raises(RuntimeError):
        await cb.call(_fail)

    await asyncio.sleep(0.02)

    with pytest.raises(RuntimeError):
        await cb.call(_fail)

    assert cb.state == "OPEN"
