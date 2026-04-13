import pytest

from src.resilience.retry import with_retry


class _StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(str(status_code))
        self.status_code = status_code


@pytest.mark.asyncio
async def test_no_retry_on_success() -> None:
    calls = 0

    async def _fn() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await with_retry(_fn, retry_count=3, backoff_seconds=0.0, retryable_codes={503})
    assert result == "ok"
    assert calls == 1


@pytest.mark.asyncio
async def test_retry_stateful_first_fails_then_succeeds() -> None:
    calls = 0

    async def _fn() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _StatusError(503)
        return "ok"

    result = await with_retry(_fn, retry_count=3, backoff_seconds=0.0, retryable_codes={503})
    assert result == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_no_retry_for_non_retryable_code() -> None:
    calls = 0

    async def _fn() -> str:
        nonlocal calls
        calls += 1
        raise _StatusError(400)

    with pytest.raises(_StatusError) as exc_info:
        await with_retry(_fn, retry_count=3, backoff_seconds=0.0, retryable_codes={503})

    assert exc_info.value.status_code == 400
    assert calls == 1


@pytest.mark.asyncio
async def test_retry_exhausted_raises_last_exception() -> None:
    calls = 0

    async def _fn() -> str:
        nonlocal calls
        calls += 1
        raise _StatusError(503)

    with pytest.raises(_StatusError) as exc_info:
        await with_retry(_fn, retry_count=2, backoff_seconds=0.0, retryable_codes={503})

    assert exc_info.value.status_code == 503
    assert calls == 3


@pytest.mark.asyncio
async def test_retry_only_on_configured_codes() -> None:
    calls_503: list[int] = []
    calls_429: list[int] = []

    async def _fn_503() -> str:
        calls_503.append(1)
        raise _StatusError(503)

    async def _fn_429() -> str:
        calls_429.append(1)
        raise _StatusError(429)

    with pytest.raises(_StatusError):
        await with_retry(_fn_503, retry_count=2, backoff_seconds=0.0, retryable_codes={503})
    assert len(calls_503) == 3

    with pytest.raises(_StatusError):
        await with_retry(_fn_429, retry_count=2, backoff_seconds=0.0, retryable_codes={503})
    assert len(calls_429) == 1
