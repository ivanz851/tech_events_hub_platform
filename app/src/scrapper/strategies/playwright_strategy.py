from __future__ import annotations
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from src.scrapper.strategies.abstract import AbstractScrapperStrategy, LinkValidationError

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

__all__ = ("PlaywrightScrapperStrategy",)

_MAX_CONTENT_LEN = 15_000
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class PlaywrightScrapperStrategy(AbstractScrapperStrategy):
    def __init__(self, context: BrowserContext, timeout_seconds: float = 20.0) -> None:
        self._context = context
        self._timeout_ms = int(timeout_seconds * 1000)

    async def validate(self, url: str) -> None:
        page = await self._context.new_page()
        try:
            response = await page.goto(url, timeout=self._timeout_ms, wait_until="domcontentloaded")
        except Exception as exc:
            raise LinkValidationError(url, str(exc)) from exc
        finally:
            await page.close()
        if response is None or not response.ok:
            status = response.status if response is not None else 0
            raise LinkValidationError(url, f"HTTP {status}")

    async def fetch_content(self, url: str) -> str:
        page = await self._context.new_page()
        try:
            response = await page.goto(url, timeout=self._timeout_ms, wait_until="networkidle")
            html = await page.content()
        except Exception as exc:
            raise LinkValidationError(url, str(exc)) from exc
        finally:
            await page.close()
        if response is None or not response.ok:
            status = response.status if response is not None else 0
            raise LinkValidationError(url, f"HTTP {status}")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(strip=True)[:_MAX_CONTENT_LEN]
