from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.metrics import detect_link_type

if TYPE_CHECKING:
    from src.scrapper.strategies.abstract import AbstractScrapperStrategy
    from src.scrapper.strategies.playwright_strategy import PlaywrightScrapperStrategy
    from src.scrapper.strategies.telegram import TelegramScrapperStrategy
    from src.scrapper.strategies.web import WebScrapperStrategy

__all__ = ("StrategyFactory",)

_JS_FALLBACK_THRESHOLD = 200


@dataclass
class StrategyFactory:
    tg_strategy: TelegramScrapperStrategy
    web_strategy: WebScrapperStrategy
    playwright_strategy: PlaywrightScrapperStrategy | None = None

    def get(self, url: str) -> AbstractScrapperStrategy:
        if detect_link_type(url) == "telegram":
            return self.tg_strategy
        return self.web_strategy

    async def fetch_with_fallback(self, url: str) -> str:
        content = await self.web_strategy.fetch_content(url)
        if len(content) < _JS_FALLBACK_THRESHOLD and self.playwright_strategy is not None:
            content = await self.playwright_strategy.fetch_content(url)
        return content
