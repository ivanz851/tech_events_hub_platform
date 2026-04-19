import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.scrapper.api import router as scrapper_router
from src.scrapper.auth.jwt_utils import create_jwt
from src.scrapper.auth.linking_cache import InMemoryLinkingCache
from src.scrapper.repository.in_memory import InMemoryLinkRepository


def _make_app() -> tuple[FastAPI, InMemoryLinkRepository]:
    from unittest.mock import MagicMock

    from src.scrapper.auth.yandex_client import YandexOAuthClient

    app = FastAPI(title="test_scrapper")
    repo = InMemoryLinkRepository()
    app.state.repository = repo
    app.state.jwt_secret = "test-secret"
    app.state.jwt_expire_minutes = 60
    app.state.linking_cache = InMemoryLinkingCache()
    app.state.yandex_oauth_client = MagicMock(spec=YandexOAuthClient)
    app.include_router(router=scrapper_router)
    return app, repo


@pytest.mark.asyncio
async def test_get_profile_returns_user_data() -> None:
    app, repo = _make_app()
    uid = await repo.get_or_create_by_telegram(999)
    token = create_jwt(uid, "test-secret", 60)

    with TestClient(app) as client:
        response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(uid)
    assert "telegram" in data["providers"]
    assert data["settings"]["notify_telegram"] is True
    assert data["settings"]["notify_email"] is False


@pytest.mark.asyncio
async def test_patch_settings_updates_notify_email() -> None:
    app, repo = _make_app()
    uid = await repo.get_or_create_by_telegram(888)
    token = create_jwt(uid, "test-secret", 60)

    with TestClient(app) as client:
        response = client.patch(
            "/users/me/settings",
            json={"notify_email": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        profile_resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert profile_resp.status_code == 200
        assert profile_resp.json()["settings"]["notify_email"] is True
        assert profile_resp.json()["settings"]["notify_telegram"] is True


@pytest.mark.asyncio
async def test_patch_settings_can_disable_telegram() -> None:
    app, repo = _make_app()
    uid = await repo.get_or_create_by_telegram(777)
    token = create_jwt(uid, "test-secret", 60)

    with TestClient(app) as client:
        response = client.patch(
            "/users/me/settings",
            json={"notify_telegram": False, "notify_email": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        profile_resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        data = profile_resp.json()
        assert data["settings"]["notify_telegram"] is False
        assert data["settings"]["notify_email"] is True
