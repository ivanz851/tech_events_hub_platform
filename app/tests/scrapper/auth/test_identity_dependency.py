from __future__ import annotations
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.scrapper.api import router as scrapper_router
from src.scrapper.auth.jwt_utils import create_jwt
from src.scrapper.repository.in_memory import InMemoryLinkRepository

_SECRET = "test-secret"
_EXPIRE = 60


def _make_app(repo: InMemoryLinkRepository) -> FastAPI:
    app = FastAPI(title="test")
    app.state.repository = repo
    app.state.jwt_secret = _SECRET
    app.state.jwt_expire_minutes = _EXPIRE
    app.include_router(scrapper_router)
    return app


@pytest.fixture
def repo() -> InMemoryLinkRepository:
    return InMemoryLinkRepository()


@pytest.fixture
def client(repo: InMemoryLinkRepository) -> TestClient:
    return TestClient(_make_app(repo))


def test_get_current_user_via_tg_chat_id_auto_creates(
    client: TestClient,
    repo: InMemoryLinkRepository,
) -> None:
    resp = client.get("/links", headers={"Tg-Chat-Id": "77777"})
    assert resp.status_code == 200
    assert resp.json()["size"] == 0


@pytest.mark.asyncio
async def test_get_current_user_via_tg_chat_id_finds_existing(
    repo: InMemoryLinkRepository,
) -> None:
    await repo.register_chat(12345)
    user_id_first = await repo.get_or_create_by_telegram(12345)
    user_id_second = await repo.get_or_create_by_telegram(12345)
    assert user_id_first == user_id_second


def test_get_current_user_via_bearer_jwt(
    repo: InMemoryLinkRepository,
) -> None:
    user_id = uuid.uuid4()
    token = create_jwt(user_id, _SECRET, _EXPIRE)
    app = _make_app(repo)
    repo._links[user_id] = {}
    with TestClient(app) as client:
        resp = client.get("/links", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_get_current_user_invalid_jwt_returns_401(
    repo: InMemoryLinkRepository,
) -> None:
    app = _make_app(repo)
    with TestClient(app) as client:
        resp = client.get("/links", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


def test_get_current_user_no_auth_returns_401(
    repo: InMemoryLinkRepository,
) -> None:
    app = _make_app(repo)
    with TestClient(app) as client:
        resp = client.get("/links")
    assert resp.status_code == 401
