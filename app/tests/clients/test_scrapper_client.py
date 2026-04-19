from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clients.scrapper import (
    LinkAlreadyTrackedError,
    ScrapperClient,
    ScrapperClientError,
)
from src.scrapper.models import SubscriptionFilters

BASE_URL = "http://scrapper-test"


@pytest.fixture
def client() -> ScrapperClient:
    return ScrapperClient(base_url=BASE_URL)


def _make_http_mock(
    status_code: int,
    json_body: dict[str, Any] | None = None,
    text: str = "",
) -> AsyncMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text
    if json_body is not None:
        response.json.return_value = json_body

    http_client = AsyncMock(spec=httpx.AsyncClient)
    http_client.__aenter__ = AsyncMock(return_value=http_client)
    http_client.__aexit__ = AsyncMock(return_value=False)
    http_client.post = AsyncMock(return_value=response)
    http_client.get = AsyncMock(return_value=response)
    http_client.delete = AsyncMock(return_value=response)
    http_client.request = AsyncMock(return_value=response)
    return http_client


@pytest.mark.asyncio
async def test_register_chat_success(client: ScrapperClient) -> None:
    mock_http = _make_http_mock(HTTPStatus.OK)
    with patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http):
        await client.register_chat(42)
    mock_http.post.assert_called_once()


@pytest.mark.asyncio
async def test_register_chat_already_exists_no_error(client: ScrapperClient) -> None:
    mock_http = _make_http_mock(HTTPStatus.CONFLICT)
    with patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http):
        await client.register_chat(42)


@pytest.mark.asyncio
async def test_register_chat_server_error(client: ScrapperClient) -> None:
    mock_http = _make_http_mock(HTTPStatus.INTERNAL_SERVER_ERROR, text="error")
    with (
        patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http),
        pytest.raises(ScrapperClientError) as exc_info,
    ):
        await client.register_chat(42)
    assert exc_info.value.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_links_success(client: ScrapperClient) -> None:
    body = {
        "links": [{"id": 1, "url": "https://t.me/ch", "filters": {"categories": ["py"]}}],
        "size": 1,
    }
    mock_http = _make_http_mock(HTTPStatus.OK, json_body=body)
    with patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http):
        links = await client.get_links(chat_id=1)
    assert len(links) == 1
    assert links[0].url == "https://t.me/ch"
    assert links[0].filters is not None
    assert links[0].filters.categories == ["py"]


@pytest.mark.asyncio
async def test_get_links_error(client: ScrapperClient) -> None:
    mock_http = _make_http_mock(HTTPStatus.NOT_FOUND, text="not found")
    with (
        patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http),
        pytest.raises(ScrapperClientError) as exc_info,
    ):
        await client.get_links(chat_id=99)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_add_link_success(client: ScrapperClient) -> None:
    body = {"id": 1, "url": "https://t.me/ch", "filters": {"categories": ["py"]}}
    mock_http = _make_http_mock(HTTPStatus.OK, json_body=body)
    with patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http):
        result = await client.add_link(1, "https://t.me/ch", SubscriptionFilters(categories=["py"]))
    assert result.url == "https://t.me/ch"
    assert result.filters is not None
    assert result.filters.categories == ["py"]


@pytest.mark.asyncio
async def test_add_link_duplicate(client: ScrapperClient) -> None:
    mock_http = _make_http_mock(HTTPStatus.CONFLICT, text="conflict")
    with (
        patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http),
        pytest.raises(LinkAlreadyTrackedError),
    ):
        await client.add_link(1, "https://t.me/ch")


@pytest.mark.asyncio
async def test_add_link_invalid_body(client: ScrapperClient) -> None:
    mock_http = _make_http_mock(HTTPStatus.BAD_REQUEST, text="bad request")
    with (
        patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http),
        pytest.raises(ScrapperClientError) as exc_info,
    ):
        await client.add_link(1, "bad")
    assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_remove_link_success(client: ScrapperClient) -> None:
    body = {"id": 1, "url": "https://t.me/ch", "filters": None}
    mock_http = _make_http_mock(HTTPStatus.OK, json_body=body)
    with patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http):
        result = await client.remove_link(1, "https://t.me/ch")
    assert result.url == "https://t.me/ch"


@pytest.mark.asyncio
async def test_remove_link_not_found(client: ScrapperClient) -> None:
    mock_http = _make_http_mock(HTTPStatus.NOT_FOUND, text="not found")
    with (
        patch("src.clients.scrapper.httpx.AsyncClient", return_value=mock_http),
        pytest.raises(ScrapperClientError) as exc_info,
    ):
        await client.remove_link(1, "https://t.me/nope")
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_register_chat_connect_error(client: ScrapperClient) -> None:
    with (
        patch(
            "src.clients.scrapper.httpx.AsyncClient",
            side_effect=httpx.ConnectError("Connection refused"),
        ),
        pytest.raises(ScrapperClientError) as exc_info,
    ):
        await client.register_chat(42)
    assert exc_info.value.status_code == 0


@pytest.mark.asyncio
async def test_get_links_connect_error(client: ScrapperClient) -> None:
    with (
        patch(
            "src.clients.scrapper.httpx.AsyncClient",
            side_effect=httpx.ConnectError("Connection refused"),
        ),
        pytest.raises(ScrapperClientError) as exc_info,
    ):
        await client.get_links(chat_id=1)
    assert exc_info.value.status_code == 0


@pytest.mark.asyncio
async def test_add_link_connect_error(client: ScrapperClient) -> None:
    with (
        patch(
            "src.clients.scrapper.httpx.AsyncClient",
            side_effect=httpx.ConnectError("Connection refused"),
        ),
        pytest.raises(ScrapperClientError) as exc_info,
    ):
        await client.add_link(1, "https://t.me/ch")
    assert exc_info.value.status_code == 0


@pytest.mark.asyncio
async def test_remove_link_connect_error(client: ScrapperClient) -> None:
    with (
        patch(
            "src.clients.scrapper.httpx.AsyncClient",
            side_effect=httpx.ConnectError("Connection refused"),
        ),
        pytest.raises(ScrapperClientError) as exc_info,
    ):
        await client.remove_link(1, "https://t.me/ch")
    assert exc_info.value.status_code == 0
