import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from .schemas import ApiErrorResponse, LinkUpdate

__all__ = ("router",)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/updates", status_code=status.HTTP_200_OK)
async def updates_handler(request: Request, update: LinkUpdate) -> dict[str, str]:
    tg_client = getattr(request.app, "tg_client", None)

    if tg_client is None:
        logger.warning("Telegram client not available, skipping notification delivery")
        return {"status": "ok"}

    message = _format_update_message(update)
    for chat_id in update.tgChatIds:
        try:
            await tg_client.send_message(chat_id, message)
            logger.info("Sent update notification", extra={"chat_id": chat_id, "url": update.url})
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to send notification",
                extra={"chat_id": chat_id, "error": str(exc)},
            )

    return {"status": "ok"}


@router.post("/updates/validate")
async def validate_update(update: LinkUpdate) -> JSONResponse:
    if not update.url or not update.tgChatIds:
        error = ApiErrorResponse(
            description="Invalid update payload",
            code="400",
            exceptionName="ValidationError",
            exceptionMessage="url and tgChatIds are required",
        )
        return JSONResponse(status_code=400, content=error.model_dump())
    return JSONResponse(status_code=200, content={"status": "valid"})


def _format_update_message(update: LinkUpdate) -> str:
    return f"Новое обновление по ссылке {update.url}:\n{update.description}"
