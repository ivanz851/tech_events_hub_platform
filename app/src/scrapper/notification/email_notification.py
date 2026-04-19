from __future__ import annotations
import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import TYPE_CHECKING

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from src.metrics import scrapper_email_errors_total, scrapper_emails_sent_total
from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

if TYPE_CHECKING:
    from src.scrapper.models import EventData

__all__ = ("EmailNotificationService",)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

logger = logging.getLogger(__name__)


class EmailNotificationService:
    def __init__(  # noqa: PLR0913
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        smtp_from: str,
        circuit_breaker: CircuitBreaker,
        retry_count: int = 2,
        retry_backoff_seconds: float = 1.0,
        max_concurrency: int = 10,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._smtp_from = smtp_from
        self._circuit_breaker = circuit_breaker
        self._retry_count = retry_count
        self._retry_backoff_seconds = retry_backoff_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=True,
        )

    def _render_html(self, url: str, event: EventData) -> str:
        template = self._jinja_env.get_template("event_email.html")
        return template.render(
            url=url,
            title=event.title,
            event_date=event.event_date,
            location=event.location,
            price=event.price,
            event_format=event.format,
            summary=event.summary,
        )

    async def send_emails(
        self,
        emails: list[str],
        url: str,
        event: EventData,
    ) -> None:
        if not emails:
            return
        html = self._render_html(url, event)
        subject = event.title or "Новый анонс мероприятия"

        async def _guarded(email: str) -> None:
            async with self._semaphore:
                await self._send_one(email, subject, html)

        results = await asyncio.gather(*[_guarded(e) for e in emails], return_exceptions=True)
        for r in results:
            if isinstance(r, BaseException):
                logger.error("Email send failed", extra={"error": str(r)})

    async def _send_one(self, email: str, subject: str, html: str) -> None:
        last_exc: Exception | None = None
        for attempt in range(self._retry_count + 1):
            try:
                await self._circuit_breaker.call(lambda: self._do_send(email, subject, html))
            except CircuitBreakerOpenError:  # noqa: PERF203
                scrapper_email_errors_total.inc()
                raise
            except aiosmtplib.SMTPException as exc:
                scrapper_email_errors_total.inc()
                last_exc = exc
                if attempt < self._retry_count:
                    logger.warning(
                        "Retrying email send",
                        extra={"attempt": attempt + 1, "email": email},
                    )
                    await asyncio.sleep(self._retry_backoff_seconds)
            else:
                scrapper_emails_sent_total.inc()
                return
        raise last_exc  # type: ignore[misc]

    async def _do_send(self, email: str, subject: str, html: str) -> None:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self._smtp_from
        message["To"] = email
        message.attach(MIMEText(html, "html"))
        await aiosmtplib.send(
            message,
            hostname=self._smtp_host,
            port=self._smtp_port,
            username=self._smtp_user or None,
            password=self._smtp_password or None,
            start_tls=False,
        )
