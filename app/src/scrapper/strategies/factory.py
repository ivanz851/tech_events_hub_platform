from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.metrics import detect_link_type

if TYPE_CHECKING:
    from src.scrapper.strategies.abstract import AbstractScrapperStrategy
    from src.scrapper.strategies.telegram import TelegramScrapperStrategy
    from src.scrapper.strategies.web import WebScrapperStrategy

__all__ = ("StrategyFactory",)


@dataclass
class StrategyFactory:
    tg_strategy: TelegramScrapperStrategy
    web_strategy: WebScrapperStrategy

    def get(self, url: str) -> AbstractScrapperStrategy:
        if detect_link_type(url) == "telegram":
            return self.tg_strategy
        return self.web_strategy
