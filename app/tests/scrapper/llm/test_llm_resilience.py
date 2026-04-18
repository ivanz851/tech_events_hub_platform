from unittest.mock import patch

import pytest

from src.resilience.circuit_breaker import CircuitBreaker
from src.scrapper.llm.client import YandexLLMClient


def _make_client(cb: CircuitBreaker | None = None) -> YandexLLMClient:
    return YandexLLMClient(
        api_key="test-key",
        folder_id="test-folder",
        model="yandexgpt-5.1/latest",
        circuit_breaker=cb or CircuitBreaker(),
        retry_count=2,
        retry_backoff_seconds=0.0,
        retry_on_codes={429, 500, 502, 503, 504},
    )


@pytest.mark.asyncio
async def test_retry_on_503_then_success() -> None:
    client = _make_client()
    call_count = 0

    async def _fake_call_llm(text: str, url: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            err = Exception("server error")
            err.status_code = 503  # type: ignore[attr-defined]
            raise err
        return '{"is_event": true, "title": "Meetup"}'

    with patch.object(client, "_call_llm", side_effect=_fake_call_llm):
        result = await client.analyze("some text about a meetup", "https://example.com")

    assert call_count == 2
    assert result is not None
    assert result.is_event is True


@pytest.mark.asyncio
async def test_no_retry_on_non_retryable_code() -> None:
    client = _make_client()
    call_count = 0

    async def _fake_call_llm(text: str, url: str) -> str:
        nonlocal call_count
        call_count += 1
        err = Exception("not found")
        err.status_code = 404  # type: ignore[attr-defined]
        raise err

    with patch.object(client, "_call_llm", side_effect=_fake_call_llm):
        result = await client.analyze("text", "https://example.com")

    assert call_count == 1
    assert result is None


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures() -> None:
    cb = CircuitBreaker(
        sliding_window_size=2,
        min_calls=2,
        failure_rate_threshold=100.0,
        wait_duration_seconds=999.0,
        permitted_calls_in_half_open=1,
    )
    client = _make_client(cb)

    async def _always_fail(text: str, url: str) -> str:
        err = Exception("server down")
        err.status_code = 999  # type: ignore[attr-defined]
        raise err

    with patch.object(client, "_call_llm", side_effect=_always_fail):
        await client.analyze("text", "https://a.com")
        await client.analyze("text", "https://b.com")

    assert cb.state == "OPEN"

    result = await client.analyze("text", "https://c.com")
    assert result is None


@pytest.mark.asyncio
async def test_analyze_returns_none_on_json_parse_failure() -> None:
    client = _make_client()

    async def _bad_response(text: str, url: str) -> str:
        return "this is definitely not json"

    with patch.object(client, "_call_llm", side_effect=_bad_response):
        result = await client.analyze("text", "https://example.com")

    assert result is None


@pytest.mark.asyncio
async def test_analyze_returns_none_when_all_retries_exhausted() -> None:
    client = _make_client()
    call_count = 0

    async def _always_503(text: str, url: str) -> str:
        nonlocal call_count
        call_count += 1
        err = Exception("server error")
        err.status_code = 503  # type: ignore[attr-defined]
        raise err

    with patch.object(client, "_call_llm", side_effect=_always_503):
        result = await client.analyze("text", "https://example.com")

    assert result is None
    assert call_count == 3
