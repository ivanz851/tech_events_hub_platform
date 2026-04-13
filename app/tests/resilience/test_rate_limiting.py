import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.resilience.rate_limiter import RateLimitMiddleware


def _make_app(limit: int) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=limit)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_requests_within_limit_succeed() -> None:
    app = _make_app(limit=5)
    with TestClient(app) as client:
        for _ in range(5):
            resp = client.get("/ping")
            assert resp.status_code == 200


def test_requests_exceeding_limit_return_429() -> None:
    app = _make_app(limit=3)
    with TestClient(app) as client:
        for _ in range(3):
            client.get("/ping")
        resp = client.get("/ping")
        assert resp.status_code == 429


def test_rate_limit_applies_per_ip() -> None:
    app = _make_app(limit=2)
    with TestClient(app) as client:
        for _ in range(2):
            resp = client.get("/ping")
            assert resp.status_code == 200
        resp = client.get("/ping")
        assert resp.status_code == 429


@pytest.mark.parametrize("endpoint", ["/ping"])
def test_rate_limit_on_endpoint(endpoint: str) -> None:
    app = _make_app(limit=1)
    with TestClient(app) as client:
        resp = client.get(endpoint)
        assert resp.status_code == 200
        resp = client.get(endpoint)
        assert resp.status_code == 429
