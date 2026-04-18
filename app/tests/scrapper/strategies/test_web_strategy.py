from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scrapper.strategies.abstract import LinkValidationError
from src.scrapper.strategies.web import WebScrapperStrategy


def _make_response(status_code: int = 200, text: str = "", content: bytes = b"hello") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_fetch_content_strips_script_tags() -> None:
    html = "<html><body><script>alert(1)</script><p>Hello world</p></body></html>"
    mock_resp = _make_response(text=html)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("src.scrapper.strategies.web.httpx.AsyncClient", return_value=mock_client):
        strategy = WebScrapperStrategy()
        result = await strategy.fetch_content("https://example.com")

    assert "Hello world" in result
    assert "alert(1)" not in result


@pytest.mark.asyncio
async def test_fetch_content_strips_style_tags() -> None:
    html = "<html><head><style>.x { color: red; }</style></head><body><p>Content</p></body></html>"
    mock_resp = _make_response(text=html)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("src.scrapper.strategies.web.httpx.AsyncClient", return_value=mock_client):
        strategy = WebScrapperStrategy()
        result = await strategy.fetch_content("https://example.com")

    assert "Content" in result
    assert ".x" not in result
    assert "color: red" not in result


@pytest.mark.asyncio
async def test_fetch_content_truncates_long_content() -> None:
    long_text = "a" * 20_000
    html = f"<html><body><p>{long_text}</p></body></html>"
    mock_resp = _make_response(text=html)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("src.scrapper.strategies.web.httpx.AsyncClient", return_value=mock_client):
        strategy = WebScrapperStrategy()
        result = await strategy.fetch_content("https://example.com")

    assert len(result) <= 15_000


@pytest.mark.asyncio
async def test_validate_raises_on_4xx_response() -> None:
    mock_resp = _make_response(status_code=404, content=b"not found")
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("src.scrapper.strategies.web.httpx.AsyncClient", return_value=mock_client):
        strategy = WebScrapperStrategy()
        with pytest.raises(LinkValidationError):
            await strategy.validate("https://example.com/notfound")


@pytest.mark.asyncio
async def test_validate_succeeds_on_200() -> None:
    mock_resp = _make_response(status_code=200, content=b"<html>ok</html>")
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("src.scrapper.strategies.web.httpx.AsyncClient", return_value=mock_client):
        strategy = WebScrapperStrategy()
        await strategy.validate("https://example.com")
