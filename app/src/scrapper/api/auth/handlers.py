from __future__ import annotations
import logging
import secrets
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from src.scrapper.api.schemas import ApiErrorResponse
from src.scrapper.auth.dependencies import get_current_user
from src.scrapper.auth.jwt_utils import create_jwt
from src.scrapper.auth.yandex_client import YandexOAuthClient, YandexOAuthError

if TYPE_CHECKING:
    from uuid import UUID

    from src.scrapper.auth.linking_cache import AbstractLinkingCache
    from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("router",)

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)

_LINK_TOKEN_TTL = 600


class LinkTelegramRequest(BaseModel):
    link_token: str
    tg_chat_id: int


def _get_repository(request: Request) -> AbstractLinkRepository:
    return request.app.state.repository  # type: ignore[no-any-return]


def _get_linking_cache(request: Request) -> AbstractLinkingCache:
    return request.app.state.linking_cache  # type: ignore[no-any-return]


def _get_yandex_client(request: Request) -> YandexOAuthClient:
    return request.app.state.yandex_oauth_client  # type: ignore[no-any-return]


@router.get("/yandex/login", status_code=status.HTTP_302_FOUND)
async def yandex_login(request: Request) -> RedirectResponse:
    client = _get_yandex_client(request)
    return RedirectResponse(url=client.get_authorization_url(), status_code=302)


@router.get("/yandex/callback", status_code=status.HTTP_200_OK)
async def yandex_callback(code: str, request: Request) -> JSONResponse:
    repository = _get_repository(request)
    client = _get_yandex_client(request)
    try:
        user_info = await client.exchange_code(code)
    except YandexOAuthError as exc:
        error = ApiErrorResponse(
            description="OAuth failed",
            code="400",
            exceptionName="YandexOAuthError",
            exceptionMessage=str(exc),
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    user_id = await repository.get_or_create_by_yandex(user_info.yandex_id, user_info.email)
    secret: str = request.app.state.jwt_secret
    expire_minutes: int = request.app.state.jwt_expire_minutes
    token = create_jwt(user_id, secret, expire_minutes)
    logger.info("OAuth login", extra={"yandex_id": user_info.yandex_id})
    return JSONResponse(status_code=200, content={"access_token": token})


@router.post("/telegram/link-token", status_code=status.HTTP_200_OK)
async def generate_link_token(
    request: Request,
    user_id: UUID = Depends(get_current_user),
) -> JSONResponse:
    cache = _get_linking_cache(request)
    token = secrets.token_urlsafe(16)
    await cache.save_link_token(token, user_id, _LINK_TOKEN_TTL)
    logger.info("Generated link token", extra={"user_id": str(user_id)})
    return JSONResponse(status_code=200, content={"link_token": token})


@router.post("/telegram/link", status_code=status.HTTP_200_OK)
async def link_telegram(body: LinkTelegramRequest, request: Request) -> JSONResponse:
    cache = _get_linking_cache(request)
    repository = _get_repository(request)

    user_id = await cache.get_user_id_by_token(body.link_token)
    if user_id is None:
        error = ApiErrorResponse(
            description="Invalid or expired link token",
            code="400",
            exceptionName="InvalidLinkTokenError",
            exceptionMessage="Token not found or expired",
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    await repository.link_telegram_to_user(user_id, body.tg_chat_id)
    await cache.delete_token(body.link_token)
    logger.info(
        "Linked telegram to user",
        extra={"user_id": str(user_id), "chat_id": body.tg_chat_id},
    )
    return JSONResponse(status_code=200, content={"status": "ok"})
