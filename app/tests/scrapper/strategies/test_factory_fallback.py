from unittest.mock import AsyncMock, MagicMock

import pytest

from src.scrapper.strategies.factory import StrategyFactory
from src.scrapper.strategies.playwright_strategy import PlaywrightScrapperStrategy
from src.scrapper.strategies.telegram import TelegramScrapperStrategy
from src.scrapper.strategies.web import WebScrapperStrategy


def _make_factory(
    web_content: str,
    playwright_content: str = "playwright result",
    playwright_enabled: bool = True,
) -> StrategyFactory:
    tg_strategy = MagicMock(spec=TelegramScrapperStrategy)
    web_strategy = MagicMock(spec=WebScrapperStrategy)
    web_strategy.fetch_content = AsyncMock(return_value=web_content)

    playwright_strategy: PlaywrightScrapperStrategy | None = None
    if playwright_enabled:
        pw = MagicMock(spec=PlaywrightScrapperStrategy)
        pw.fetch_content = AsyncMock(return_value=playwright_content)
        playwright_strategy = pw

    return StrategyFactory(
        tg_strategy=tg_strategy,
        web_strategy=web_strategy,
        playwright_strategy=playwright_strategy,
    )


@pytest.mark.asyncio
async def test_fallback_not_triggered_when_content_sufficient() -> None:
    long_content = "x" * 300
    factory = _make_factory(web_content=long_content)

    result = await factory.fetch_with_fallback("https://example.com")

    assert result == long_content
    factory.playwright_strategy.fetch_content.assert_not_called()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_fallback_triggered_when_content_too_short() -> None:
    short_content = "short"
    playwright_result = "full js content " * 20
    factory = _make_factory(web_content=short_content, playwright_content=playwright_result)

    result = await factory.fetch_with_fallback("https://example.com")

    assert result == playwright_result
    factory.playwright_strategy.fetch_content.assert_called_once_with("https://example.com")  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_fallback_not_triggered_when_playwright_not_configured() -> None:
    short_content = "short"
    factory = _make_factory(web_content=short_content, playwright_enabled=False)

    result = await factory.fetch_with_fallback("https://example.com")

    assert result == short_content


@pytest.mark.asyncio
async def test_fallback_boundary_exactly_200_chars_no_fallback() -> None:
    content_200 = "a" * 200
    factory = _make_factory(web_content=content_200)

    result = await factory.fetch_with_fallback("https://example.com")

    assert result == content_200
    factory.playwright_strategy.fetch_content.assert_not_called()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_fallback_boundary_199_chars_triggers_fallback() -> None:
    content_199 = "a" * 199
    playwright_result = "playwright full content"
    factory = _make_factory(web_content=content_199, playwright_content=playwright_result)

    result = await factory.fetch_with_fallback("https://example.com")

    assert result == playwright_result
