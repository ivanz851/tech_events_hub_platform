from __future__ import annotations
import json
import logging
import re
import time
from typing import TYPE_CHECKING, ClassVar

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.metrics import scrapper_llm_errors_total, scrapper_llm_generation_duration_seconds
from src.resilience.retry import with_retry

if TYPE_CHECKING:
    from src.resilience.circuit_breaker import CircuitBreaker

__all__ = ("LLMEventResult", "YandexLLMClient", "parse_llm_response")

logger = logging.getLogger(__name__)

_MAX_TEXT_LENGTH: int = 30_000

_SYSTEM_PROMPT = (
    "You are an IT event analyzer. Given an announcement text and a URL, "
    "extract structured data.\n\n"
    "If the text is NOT about an IT event "
    "(conference, meetup, hackathon, webinar, workshop, etc.), "
    'return exactly: {"is_event": false}\n\n'
    "Otherwise return a JSON object with these fields:\n"
    "{\n"
    '  "is_event": true,\n'
    '  "title": "event name or null",\n'
    '  "event_date": "date/time string or null",\n'
    '  "location": "city/venue/online or null",\n'
    '  "price": "price info or null",\n'
    '  "registration_url": "URL or null",\n'
    '  "format": "online/offline/hybrid or null",\n'
    '  "event_type": "conference/meetup/hackathon/webinar/etc or null",\n'
    '  "summary": "brief description in Russian or null",\n'
    '  "tags": ["tag1", "tag2"],\n'
    '  "organizer": "organizer name or null"\n'
    "}\n\n"
    "Return ONLY the JSON object, no other text."
)


class LLMEventResult(BaseModel):
    is_event: bool = True
    title: str | None = None
    event_date: str | None = None
    location: str | None = None
    price: str | None = None
    registration_url: str | None = None
    format: str | None = None
    event_type: str | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    organizer: str | None = None


def parse_llm_response(text: str) -> LLMEventResult:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```\s*$", "", text.strip())
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]!r}")
    data: dict[str, object] = json.loads(match.group())
    if data.get("tags") is None:
        data["tags"] = []
    return LLMEventResult.model_validate(data)


class YandexLLMClient:
    _MAX_TEXT_LENGTH: ClassVar[int] = _MAX_TEXT_LENGTH

    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str,
        circuit_breaker: CircuitBreaker,
        retry_count: int = 3,
        retry_backoff_seconds: float = 1.0,
        retry_on_codes: set[int] | None = None,
    ) -> None:
        self._folder_id = folder_id
        self._model = model
        self._cb = circuit_breaker
        self._retry_count = retry_count
        self._retry_backoff = retry_backoff_seconds
        self._retry_codes = retry_on_codes or {429, 500, 502, 503, 504}
        self._openai = AsyncOpenAI(
            api_key=api_key,
            base_url="https://ai.api.cloud.yandex.net/v1",
            project=folder_id,
            timeout=30.0,
        )

    async def analyze(self, text: str, url: str) -> LLMEventResult | None:
        truncated = text[:_MAX_TEXT_LENGTH]
        start = time.monotonic()
        raw: str | None = None

        async def _do_cb() -> str:
            async def _fn() -> str:
                return await self._call_llm(truncated, url)

            return await with_retry(
                _fn,
                retry_count=self._retry_count,
                backoff_seconds=self._retry_backoff,
                retryable_codes=self._retry_codes,
            )

        try:
            raw = await self._cb.call(_do_cb)
        except Exception:
            scrapper_llm_errors_total.inc()
            logger.exception("LLM API call failed", extra={"url": url})
        finally:
            scrapper_llm_generation_duration_seconds.observe(time.monotonic() - start)

        if raw is None:
            return None

        try:
            return parse_llm_response(raw)
        except Exception:
            scrapper_llm_errors_total.inc()
            logger.exception("Failed to parse LLM response", extra={"url": url})
            return None

    async def _call_llm(self, text: str, url: str) -> str:
        response = await self._openai.responses.create(  # type: ignore[attr-defined]
            model=f"gpt://{self._folder_id}/{self._model}",
            temperature=0.3,
            instructions=_SYSTEM_PROMPT,
            input=f"URL: {url}\n\n{text}",
            max_output_tokens=1000,
        )
        return response.output_text  # type: ignore[no-any-return]
