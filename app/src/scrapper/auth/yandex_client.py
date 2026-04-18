from __future__ import annotations
from dataclasses import dataclass
from http import HTTPStatus

import httpx

from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.resilience.retry import with_retry

__all__ = ("YandexOAuthClient", "YandexUserInfo", "YandexOAuthError")

_TOKEN_URL = "https://oauth.yandex.ru/token"  # noqa: S105
_INFO_URL = "https://login.yandex.ru/info"


@dataclass(frozen=True)
class YandexUserInfo:
    yandex_id: str
    email: str | None


class YandexOAuthError(Exception):
    pass


class YandexOAuthClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        circuit_breaker: CircuitBreaker,
        retry_count: int = 3,
        retry_backoff_seconds: float = 1.0,
        retry_on_codes: set[int] | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._cb = circuit_breaker
        self._retry_count = retry_count
        self._retry_backoff = retry_backoff_seconds
        self._retry_codes = retry_on_codes if retry_on_codes is not None else {429, 500, 502, 503}

    def get_authorization_url(self) -> str:
        return (
            f"https://oauth.yandex.ru/authorize"
            f"?response_type=code"
            f"&client_id={self._client_id}"
            f"&redirect_uri={self._redirect_uri}"
        )

    async def exchange_code(self, code: str) -> YandexUserInfo:
        async def _call() -> YandexUserInfo:
            async with httpx.AsyncClient() as client:
                token_resp = await client.post(
                    _TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "redirect_uri": self._redirect_uri,
                    },
                )
                if token_resp.status_code != HTTPStatus.OK:
                    raise YandexOAuthError(f"Token exchange failed: {token_resp.status_code}")
                access_token: str = token_resp.json()["access_token"]

                info_resp = await client.get(
                    _INFO_URL,
                    headers={"Authorization": f"OAuth {access_token}"},
                )
                if info_resp.status_code != HTTPStatus.OK:
                    raise YandexOAuthError(f"User info request failed: {info_resp.status_code}")
                data = info_resp.json()
                return YandexUserInfo(
                    yandex_id=str(data["id"]),
                    email=data.get("default_email"),
                )

        async def _with_retry() -> YandexUserInfo:
            return await with_retry(
                _call,
                retry_count=self._retry_count,
                backoff_seconds=self._retry_backoff,
                retryable_codes=self._retry_codes,
            )

        try:
            return await self._cb.call(_with_retry)
        except CircuitBreakerOpenError as exc:
            raise YandexOAuthError("Yandex OAuth unavailable") from exc
