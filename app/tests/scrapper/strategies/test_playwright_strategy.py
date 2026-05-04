from unittest.mock import AsyncMock, MagicMock

import pytest

from src.scrapper.strategies.abstract import LinkValidationError
from src.scrapper.strategies.playwright_strategy import PlaywrightScrapperStrategy


def _make_strategy(timeout_seconds: float = 20.0) -> tuple[PlaywrightScrapperStrategy, MagicMock]:
    context = MagicMock()
    strategy = PlaywrightScrapperStrategy(context=context, timeout_seconds=timeout_seconds)
    return strategy, context


@pytest.mark.asyncio
async def test_fetch_content_returns_extracted_text() -> None:
    strategy, context = _make_strategy()

    page = AsyncMock()
    page.goto = AsyncMock(return_value=MagicMock(ok=True))
    page.content = AsyncMock(return_value="<html><body><p>Hello World</p></body></html>")
    context.new_page = AsyncMock(return_value=page)

    result = await strategy.fetch_content("https://example.com")

    assert "Hello World" in result
    page.close.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_content_strips_scripts_and_style() -> None:
    strategy, context = _make_strategy()

    html = (
        "<html><head><script>alert(1)</script><style>.x{color:red}</style></head>"
        "<body><p>Clean text</p></body></html>"
    )
    page = AsyncMock()
    page.goto = AsyncMock(return_value=MagicMock(ok=True))
    page.content = AsyncMock(return_value=html)
    context.new_page = AsyncMock(return_value=page)

    result = await strategy.fetch_content("https://example.com")

    assert "alert" not in result
    assert "color" not in result
    assert "Clean text" in result


@pytest.mark.asyncio
async def test_fetch_content_raises_on_http_error() -> None:
    strategy, context = _make_strategy()

    page = AsyncMock()
    page.goto = AsyncMock(return_value=MagicMock(ok=False, status=404))
    context.new_page = AsyncMock(return_value=page)

    with pytest.raises(LinkValidationError):
        await strategy.fetch_content("https://example.com/not-found")

    page.close.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_content_raises_on_playwright_exception() -> None:
    strategy, context = _make_strategy()

    page = AsyncMock()
    page.goto = AsyncMock(side_effect=Exception("net::ERR_NAME_NOT_RESOLVED"))
    context.new_page = AsyncMock(return_value=page)

    with pytest.raises(LinkValidationError):
        await strategy.fetch_content("https://nonexistent.invalid")

    page.close.assert_called_once()


@pytest.mark.asyncio
async def test_validate_succeeds_on_ok_response() -> None:
    strategy, context = _make_strategy()

    page = AsyncMock()
    page.goto = AsyncMock(return_value=MagicMock(ok=True))
    context.new_page = AsyncMock(return_value=page)

    await strategy.validate("https://example.com")

    page.close.assert_called_once()


@pytest.mark.asyncio
async def test_validate_raises_on_failed_goto() -> None:
    strategy, context = _make_strategy()

    page = AsyncMock()
    page.goto = AsyncMock(side_effect=Exception("Timeout"))
    context.new_page = AsyncMock(return_value=page)

    with pytest.raises(LinkValidationError):
        await strategy.validate("https://example.com/slow")

    page.close.assert_called_once()
