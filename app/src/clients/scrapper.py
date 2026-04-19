from __future__ import annotations
import logging
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeVar

import httpx

from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.resilience.retry import with_retry
from src.scrapper.models import SubscriptionFilters

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

__all__ = (
    "LinkResponse",
    "ScrapperClient",
    "ScrapperClientError",
    "LinkAlreadyTrackedError",
    "LinkValidationError",
)

_T = TypeVar("_T")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LinkResponse:
    id: int
    url: str
    filters: SubscriptionFilters | None = None


class ScrapperClientError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class LinkAlreadyTrackedError(ScrapperClientError):
    pass


class LinkValidationError(ScrapperClientError):
    pass


class ScrapperClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout_seconds: float = 5.0,
        retry_count: int = 3,
        retry_backoff_seconds: float = 1.0,
        retry_on_codes: set[int] | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = httpx.Timeout(timeout_seconds)
        self._retry_count = retry_count
        self._retry_backoff = retry_backoff_seconds
        self._retry_codes = retry_on_codes if retry_on_codes is not None else {502, 503, 429}
        self._cb = circuit_breaker

    async def _execute(self, fn: Callable[[], Coroutine[Any, Any, _T]]) -> _T:
        async def _retried() -> _T:
            return await with_retry(
                fn,
                retry_count=self._retry_count,
                backoff_seconds=self._retry_backoff,
                retryable_codes=self._retry_codes,
            )

        try:
            if self._cb is not None:
                return await self._cb.call(_retried)
            return await _retried()
        except CircuitBreakerOpenError as exc:
            raise ScrapperClientError(503, str(exc)) from exc

    async def register_chat(self, chat_id: int) -> None:
        async def _call() -> None:
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout,
                ) as client:
                    resp = await client.post(f"/tg-chat/{chat_id}")
                    if resp.status_code not in (HTTPStatus.OK, HTTPStatus.CONFLICT):
                        raise ScrapperClientError(resp.status_code, resp.text)
            except httpx.RequestError as exc:
                raise ScrapperClientError(0, str(exc)) from exc

        await self._execute(_call)
        logger.info("Registered chat", extra={"chat_id": chat_id})

    async def delete_chat(self, chat_id: int) -> None:
        async def _call() -> None:
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout,
                ) as client:
                    resp = await client.delete(f"/tg-chat/{chat_id}")
                    if resp.status_code not in (HTTPStatus.OK, HTTPStatus.NOT_FOUND):
                        raise ScrapperClientError(resp.status_code, resp.text)
            except httpx.RequestError as exc:
                raise ScrapperClientError(0, str(exc)) from exc

        await self._execute(_call)
        logger.info("Deleted chat", extra={"chat_id": chat_id})

    async def get_links(self, chat_id: int) -> list[LinkResponse]:

        async def _call() -> list[LinkResponse]:
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout,
                ) as client:
                    resp = await client.get("/links", headers={"Tg-Chat-Id": str(chat_id)})
                    if resp.status_code != HTTPStatus.OK:
                        raise ScrapperClientError(resp.status_code, resp.text)
                    data = resp.json()
            except httpx.RequestError as exc:
                raise ScrapperClientError(0, str(exc)) from exc
            return [
                LinkResponse(
                    id=item["id"],
                    url=item["url"],
                    filters=(
                        SubscriptionFilters.model_validate(item["filters"])
                        if item.get("filters")
                        else None
                    ),
                )
                for item in data.get("links", [])
            ]

        return await self._execute(_call)

    async def add_link(
        self,
        chat_id: int,
        link: str,
        filters: SubscriptionFilters | None = None,
    ) -> LinkResponse:
        async def _call() -> LinkResponse:
            filters_dict = filters.model_dump(mode="json", exclude_none=True) if filters else None
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout,
                ) as client:
                    resp = await client.post(
                        "/links",
                        headers={"Tg-Chat-Id": str(chat_id)},
                        json={"link": link, "filters": filters_dict},
                    )
                    if resp.status_code == HTTPStatus.CONFLICT:
                        raise LinkAlreadyTrackedError(HTTPStatus.CONFLICT, "Link already tracked")
                    if resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                        raise LinkValidationError(
                            HTTPStatus.UNPROCESSABLE_ENTITY,
                            "Link validation failed",
                        )
                    if resp.status_code != HTTPStatus.OK:
                        raise ScrapperClientError(resp.status_code, resp.text)
                    data = resp.json()
            except httpx.RequestError as exc:
                raise ScrapperClientError(0, str(exc)) from exc
            return LinkResponse(
                id=data["id"],
                url=data["url"],
                filters=(
                    SubscriptionFilters.model_validate(data["filters"])
                    if data.get("filters")
                    else None
                ),
            )

        result = await self._execute(_call)
        logger.info("Added link", extra={"chat_id": chat_id, "url": link})
        return result

    async def link_telegram(self, link_token: str, tg_chat_id: int) -> None:
        async def _call() -> None:
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout,
                ) as client:
                    resp = await client.post(
                        "/auth/telegram/link",
                        json={"link_token": link_token, "tg_chat_id": tg_chat_id},
                    )
                    if resp.status_code != HTTPStatus.OK:
                        raise ScrapperClientError(resp.status_code, resp.text)
            except httpx.RequestError as exc:
                raise ScrapperClientError(0, str(exc)) from exc

        await self._execute(_call)
        logger.info("Linked telegram", extra={"tg_chat_id": tg_chat_id})

    async def remove_link(self, chat_id: int, link: str) -> LinkResponse:
        async def _call() -> LinkResponse:
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout,
                ) as client:
                    resp = await client.request(
                        "DELETE",
                        "/links",
                        headers={"Tg-Chat-Id": str(chat_id)},
                        json={"link": link},
                    )
                    if resp.status_code == HTTPStatus.NOT_FOUND:
                        raise ScrapperClientError(HTTPStatus.NOT_FOUND, "Link not found")
                    if resp.status_code != HTTPStatus.OK:
                        raise ScrapperClientError(resp.status_code, resp.text)
                    data = resp.json()
            except httpx.RequestError as exc:
                raise ScrapperClientError(0, str(exc)) from exc
            return LinkResponse(
                id=data["id"],
                url=data["url"],
                filters=(
                    SubscriptionFilters.model_validate(data["filters"])
                    if data.get("filters")
                    else None
                ),
            )

        result = await self._execute(_call)
        logger.info("Removed link", extra={"chat_id": chat_id, "url": link})
        return result
