from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from src.scrapper.strategies.abstract import AbstractScrapperStrategy, LinkValidationError

__all__ = ("WebScrapperStrategy",)

_MAX_CONTENT_LEN = 15_000
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class WebScrapperStrategy(AbstractScrapperStrategy):
    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)

    async def validate(self, url: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": _USER_AGENT},
                    follow_redirects=True,
                )
                if resp.status_code >= 400:  # noqa: PLR2004
                    raise LinkValidationError(url, f"HTTP {resp.status_code}")
                if not resp.content:
                    raise LinkValidationError(url, "Empty response")
        except httpx.RequestError as exc:
            raise LinkValidationError(url, str(exc)) from exc

    async def fetch_content(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": _USER_AGENT},
                    follow_redirects=True,
                )
                resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            raise LinkValidationError(url, str(exc)) from exc
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(strip=True)[:_MAX_CONTENT_LEN]
