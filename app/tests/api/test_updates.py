from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import router


@pytest.fixture
def app_with_tg_client() -> FastAPI:
    app = FastAPI()
    app.include_router(router=router, prefix="/api/v1")
    mock_client = AsyncMock()
    mock_client.send_message = AsyncMock()
    app.tg_client = mock_client  # type: ignore[attr-defined]
    return app


@pytest.fixture
def client_with_tg(app_with_tg_client: FastAPI) -> TestClient:
    return TestClient(app_with_tg_client)


def test_updates_valid_payload(client_with_tg: TestClient) -> None:
    payload = {
        "id": 1,
        "url": "https://t.me/ch",
        "description": "New event",
        "tgChatIds": [111, 222],
    }
    resp = client_with_tg.post("/api/v1/updates", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_updates_invalid_payload_returns_422(test_client: TestClient) -> None:
    resp = test_client.post("/api/v1/updates", json={"id": "not-int"})
    assert resp.status_code == 422


def test_updates_empty_chat_ids(client_with_tg: TestClient) -> None:
    payload = {
        "id": 1,
        "url": "https://t.me/ch",
        "description": "text",
        "tgChatIds": [],
    }
    resp = client_with_tg.post("/api/v1/updates", json=payload)
    assert resp.status_code == 200
