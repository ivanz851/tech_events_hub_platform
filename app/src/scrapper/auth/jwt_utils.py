from __future__ import annotations
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

__all__ = ("create_jwt", "verify_jwt", "InvalidTokenError")


class InvalidTokenError(Exception):
    pass


def create_jwt(user_id: UUID, secret: str, expire_minutes: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")  # type: ignore[return-value]


def verify_jwt(token: str, secret: str) -> UUID:
    try:
        payload: dict[str, object] = jwt.decode(token, secret, algorithms=["HS256"])
        return UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise InvalidTokenError("Invalid token") from exc
