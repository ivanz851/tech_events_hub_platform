from collections.abc import Generator
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.scrapper.api import router as scrapper_router
from src.scrapper.repository.in_memory import InMemoryLinkRepository
from src.scrapper.strategies.abstract import LinkValidationError
from src.scrapper.strategies.factory import StrategyFactory


def _make_app(
    repository: InMemoryLinkRepository,
    *,
    validation_fails: bool = False,
    has_factory: bool = True,
) -> FastAPI:
    app = FastAPI(title="scrapper_app")
    app.state.repository = repository
    if has_factory:
        strategy = AsyncMock()
        if validation_fails:
            strategy.validate = AsyncMock(
                side_effect=LinkValidationError("https://bad.example.com", "not accessible"),
            )
        else:
            strategy.validate = AsyncMock(return_value=None)
        factory = MagicMock(spec=StrategyFactory)
        factory.get.return_value = strategy
        app.state.strategy_factory = factory
    app.include_router(scrapper_router)
    return app


@pytest.fixture
def chat_id() -> int:
    return 77


@pytest.fixture
def client_valid(chat_id: int) -> Generator[TestClient, None, None]:
    repo = InMemoryLinkRepository()
    app = _make_app(repo, validation_fails=False)
    with TestClient(app) as client:
        client.post(f"/tg-chat/{chat_id}")
        yield client


@pytest.fixture
def client_invalid(chat_id: int) -> Generator[TestClient, None, None]:
    repo = InMemoryLinkRepository()
    app = _make_app(repo, validation_fails=True)
    with TestClient(app) as client:
        client.post(f"/tg-chat/{chat_id}")
        yield client


def test_add_link_unavailable_url_returns_422(client_invalid: TestClient, chat_id: int) -> None:
    resp = client_invalid.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://bad.example.com", "tags": [], "filters": []},
    )
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    data = resp.json()
    assert data["exception_name"] == "LinkValidationError"


def test_add_link_unavailable_url_not_saved_to_db(client_invalid: TestClient, chat_id: int) -> None:
    client_invalid.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://bad.example.com", "tags": [], "filters": []},
    )
    links_resp = client_invalid.get("/links", headers={"Tg-Chat-Id": str(chat_id)})
    assert links_resp.json()["size"] == 0


def test_add_link_valid_url_returns_200(client_valid: TestClient, chat_id: int) -> None:
    resp = client_valid.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://example.com", "tags": [], "filters": []},
    )
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["url"] == "https://example.com"


def test_add_link_valid_url_saved_to_db(client_valid: TestClient, chat_id: int) -> None:
    client_valid.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://example.com", "tags": [], "filters": []},
    )
    links_resp = client_valid.get("/links", headers={"Tg-Chat-Id": str(chat_id)})
    assert links_resp.json()["size"] == 1


def test_add_link_no_factory_skips_validation(chat_id: int) -> None:
    repo = InMemoryLinkRepository()
    app = _make_app(repo, has_factory=False)
    with TestClient(app) as client:
        client.post(f"/tg-chat/{chat_id}")
        resp = client.post(
            "/links",
            headers={"Tg-Chat-Id": str(chat_id)},
            json={"link": "https://t.me/ch", "tags": [], "filters": []},
        )
    assert resp.status_code == HTTPStatus.OK
