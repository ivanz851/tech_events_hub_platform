from unittest.mock import AsyncMock, patch

import aiosmtplib
import pytest

from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.scrapper.models import EventData
from src.scrapper.notification.email_notification import EmailNotificationService


def _make_service(
    retry_count: int = 1,
    cb: CircuitBreaker | None = None,
) -> EmailNotificationService:
    if cb is None:
        cb = CircuitBreaker(
            sliding_window_size=10,
            min_calls=10,
            failure_rate_threshold=100.0,
            wait_duration_seconds=60.0,
        )
    return EmailNotificationService(
        smtp_host="localhost",
        smtp_port=1025,
        smtp_user="",
        smtp_password="",
        smtp_from="test@local",
        circuit_breaker=cb,
        retry_count=retry_count,
        retry_backoff_seconds=0.0,
        max_concurrency=10,
    )


@pytest.mark.asyncio
async def test_send_emails_renders_jinja2_and_calls_smtp() -> None:
    service = _make_service()
    event = EventData(title="PyCon 2025", summary="Great Python conference", location="Moscow")

    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        await service.send_emails(["test@example.com"], "https://example.com", event)

    mock_send.assert_called_once()
    call_args = mock_send.call_args
    message = call_args.args[0]
    html_payload = message.get_payload(0).get_payload(decode=True).decode("utf-8")
    assert "PyCon 2025" in html_payload
    assert "Moscow" in html_payload


@pytest.mark.asyncio
async def test_send_emails_empty_list_does_nothing() -> None:
    service = _make_service()
    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        await service.send_emails([], "https://example.com", EventData())
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_smtp_error_retries_and_circuit_breaker_opens() -> None:
    cb = CircuitBreaker(
        sliding_window_size=2,
        min_calls=2,
        failure_rate_threshold=100.0,
        wait_duration_seconds=60.0,
        permitted_calls_in_half_open=1,
    )
    service = _make_service(retry_count=1, cb=cb)

    with (
        patch("aiosmtplib.send", side_effect=aiosmtplib.SMTPConnectError("conn failed")),
        pytest.raises(aiosmtplib.SMTPConnectError),
    ):
        await service._send_one("a@b.com", "Subject", "<html></html>")

    assert cb.state == "OPEN"


@pytest.mark.asyncio
async def test_send_emails_failure_does_not_crash_process() -> None:
    service = _make_service(retry_count=0)
    with patch("aiosmtplib.send", side_effect=aiosmtplib.SMTPConnectError("fail")):
        await service.send_emails(["a@b.com"], "https://example.com", EventData())


@pytest.mark.asyncio
async def test_circuit_breaker_open_raises_immediately() -> None:
    cb = CircuitBreaker(
        sliding_window_size=1,
        min_calls=1,
        failure_rate_threshold=100.0,
        wait_duration_seconds=60.0,
    )
    service = _make_service(retry_count=0, cb=cb)

    with (
        patch("aiosmtplib.send", side_effect=aiosmtplib.SMTPConnectError("fail")),
        pytest.raises(aiosmtplib.SMTPConnectError),
    ):
        await service._send_one("x@y.com", "Subj", "<html></html>")

    assert cb.state == "OPEN"

    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        with pytest.raises(CircuitBreakerOpenError):
            await service._send_one("x@y.com", "Subj", "<html></html>")
        mock_send.assert_not_called()
