from __future__ import annotations
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.scrapper.api import router as scrapper_router
from src.scrapper.auth.linking_cache import InMemoryLinkingCache
from src.scrapper.auth.yandex_client import YandexOAuthClient, YandexOAuthError, YandexUserInfo
from src.scrapper.repository.in_memory import InMemoryLinkRepository

_SECRET = "test-secret"
_EXPIRE = 60


def _make_app(repo: InMemoryLinkRepository) -> FastAPI:
    from unittest.mock import MagicMock

    app = FastAPI(title="test")
    app.state.repository = repo
    app.state.jwt_secret = _SECRET
    app.state.jwt_expire_minutes = _EXPIRE
    app.state.linking_cache = InMemoryLinkingCache()
    app.state.yandex_oauth_client = MagicMock(spec=YandexOAuthClient)
    app.include_router(scrapper_router)
    return app


@pytest.fixture
def repo() -> InMemoryLinkRepository:
    return InMemoryLinkRepository()


def test_yandex_callback_creates_user_and_returns_jwt(repo: InMemoryLinkRepository) -> None:
    app = _make_app(repo)
    app.state.yandex_oauth_client.exchange_code = AsyncMock(
        return_value=YandexUserInfo(yandex_id="ya-123", email="user@ya.ru"),
    )
    with TestClient(app) as client:
        resp = client.get("/auth/yandex/callback?code=some-code")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert len(data["access_token"]) > 0


def test_yandex_callback_same_yandex_id_returns_same_user(repo: InMemoryLinkRepository) -> None:
    import jwt as pyjwt

    app = _make_app(repo)
    app.state.yandex_oauth_client.exchange_code = AsyncMock(
        return_value=YandexUserInfo(yandex_id="ya-999", email=None),
    )
    with TestClient(app) as client:
        r1 = client.get("/auth/yandex/callback?code=code1")
        r2 = client.get("/auth/yandex/callback?code=code2")
    assert r1.status_code == 200
    assert r2.status_code == 200
    sub1 = pyjwt.decode(r1.json()["access_token"], _SECRET, algorithms=["HS256"])["sub"]
    sub2 = pyjwt.decode(r2.json()["access_token"], _SECRET, algorithms=["HS256"])["sub"]
    assert sub1 == sub2


def test_yandex_callback_oauth_error_returns_400(repo: InMemoryLinkRepository) -> None:
    app = _make_app(repo)
    app.state.yandex_oauth_client.exchange_code = AsyncMock(
        side_effect=YandexOAuthError("bad code"),
    )
    with TestClient(app) as client:
        resp = client.get("/auth/yandex/callback?code=bad")
    assert resp.status_code == 400


def test_yandex_login_redirects(repo: InMemoryLinkRepository) -> None:
    app = _make_app(repo)
    app.state.yandex_oauth_client.get_authorization_url = lambda: "https://oauth.yandex.ru/auth"
    with TestClient(app, follow_redirects=False) as client:
        resp = client.get("/auth/yandex/login")
    assert resp.status_code == 302
    assert "oauth.yandex.ru" in resp.headers["location"]
