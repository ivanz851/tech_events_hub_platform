from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import Header, HTTPException, Request

from src.scrapper.auth.jwt_utils import InvalidTokenError, verify_jwt

if TYPE_CHECKING:
    from src.scrapper.repository.abstract import AbstractLinkRepository

__all__ = ("get_current_user",)


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    tg_chat_id_header: int | None = Header(default=None, alias="Tg-Chat-Id"),
) -> UUID:
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        secret: str = request.app.state.jwt_secret
        try:
            return verify_jwt(token, secret)
        except InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc

    if tg_chat_id_header is not None:
        repository: AbstractLinkRepository = request.app.state.repository
        return await repository.get_or_create_by_telegram(tg_chat_id_header)

    raise HTTPException(status_code=401, detail="Not authenticated")
