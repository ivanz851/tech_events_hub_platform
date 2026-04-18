from __future__ import annotations
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.scrapper.api import router as scrapper_router
from src.scrapper.auth.jwt_utils import create_jwt
from src.scrapper.auth.linking_cache import InMemoryLinkingCache
from src.scrapper.auth.yandex_client import YandexOAuthClient
from src.scrapper.repository.in_memory import InMemoryLinkRepository

_SECRET = "test-secret"
_EXPIRE = 60


def _make_app(repo: InMemoryLinkRepository, cache: InMemoryLinkingCache) -> FastAPI:
    app = FastAPI(title="test")
    app.state.repository = repo
    app.state.jwt_secret = _SECRET
    app.state.jwt_expire_minutes = _EXPIRE
    app.state.linking_cache = cache
    app.state.yandex_oauth_client = MagicMock(spec=YandexOAuthClient)
    app.include_router(scrapper_router)
    return app


@pytest.fixture
def repo() -> InMemoryLinkRepository:
    return InMemoryLinkRepository()


@pytest.fixture
def cache() -> InMemoryLinkingCache:
    return InMemoryLinkingCache()


def test_generate_link_token_saves_to_cache(
    repo: InMemoryLinkRepository,
    cache: InMemoryLinkingCache,
) -> None:
    user_id = uuid.uuid4()
    repo._links[user_id] = {}
    token = create_jwt(user_id, _SECRET, _EXPIRE)
    app = _make_app(repo, cache)
    with TestClient(app) as client:
        resp = client.post(
            "/auth/telegram/link-token",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    link_token = resp.json()["link_token"]
    assert len(link_token) > 0
    assert cache._store.get(link_token) == user_id


@pytest.mark.asyncio
async def test_link_telegram_creates_identity_and_deletes_token(
    repo: InMemoryLinkRepository,
    cache: InMemoryLinkingCache,
) -> None:
    user_id = uuid.uuid4()
    repo._links[user_id] = {}
    link_token = "test-token-abc"
    await cache.save_link_token(link_token, user_id, 600)

    app = _make_app(repo, cache)
    with TestClient(app) as client:
        resp = client.post(
            "/auth/telegram/link",
            json={"link_token": link_token, "tg_chat_id": 55555},
        )
    assert resp.status_code == 200
    assert await cache.get_user_id_by_token(link_token) is None
    assert repo._telegram_to_user.get(55555) == user_id


def test_link_telegram_invalid_token_returns_400(
    repo: InMemoryLinkRepository,
    cache: InMemoryLinkingCache,
) -> None:
    app = _make_app(repo, cache)
    with TestClient(app) as client:
        resp = client.post(
            "/auth/telegram/link",
            json={"link_token": "nonexistent-token", "tg_chat_id": 99999},
        )
    assert resp.status_code == 400


def test_generate_link_token_requires_auth(
    repo: InMemoryLinkRepository,
    cache: InMemoryLinkingCache,
) -> None:
    app = _make_app(repo, cache)
    with TestClient(app) as client:
        resp = client.post("/auth/telegram/link-token")
    assert resp.status_code == 401
