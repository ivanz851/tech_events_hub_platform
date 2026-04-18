from __future__ import annotations
from abc import ABC, abstractmethod

__all__ = ("AbstractScrapperStrategy", "LinkValidationError")


class LinkValidationError(Exception):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"Cannot validate {url}: {reason}")
        self.url = url
        self.reason = reason


class AbstractScrapperStrategy(ABC):
    @abstractmethod
    async def validate(self, url: str) -> None: ...

    @abstractmethod
    async def fetch_content(self, url: str) -> str: ...
