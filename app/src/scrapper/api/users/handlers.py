from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.scrapper.api.schemas import ApiErrorResponse
from src.scrapper.auth.dependencies import get_current_user

if TYPE_CHECKING:
    from uuid import UUID

    from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("router",)

router = APIRouter(prefix="/users")
logger = logging.getLogger(__name__)


class UserSettingsUpdate(BaseModel):
    notify_email: bool | None = None
    notify_telegram: bool | None = None


def _get_repository(request: Request) -> AbstractLinkRepository:
    return request.app.state.repository  # type: ignore[no-any-return]


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_profile(
    request: Request,
    user_id: UUID = Depends(get_current_user),
) -> JSONResponse:
    repository = _get_repository(request)
    profile = await repository.get_profile(user_id)
    if profile is None:
        error = ApiErrorResponse(description="User not found", code="404")
        return JSONResponse(status_code=404, content=error.model_dump())
    return JSONResponse(
        status_code=200,
        content={
            "id": str(profile.user_id),
            "email": profile.email,
            "providers": profile.providers,
            "settings": {
                "notify_telegram": profile.notify_telegram,
                "notify_email": profile.notify_email,
            },
        },
    )


@router.patch("/me/settings", status_code=status.HTTP_200_OK)
async def update_settings(
    body: UserSettingsUpdate,
    request: Request,
    user_id: UUID = Depends(get_current_user),
) -> JSONResponse:
    repository = _get_repository(request)
    await repository.update_user_settings(
        user_id=user_id,
        notify_email=body.notify_email,
        notify_telegram=body.notify_telegram,
    )
    logger.info("User settings updated", extra={"user_id": str(user_id)})
    return JSONResponse(status_code=200, content={"status": "ok"})
