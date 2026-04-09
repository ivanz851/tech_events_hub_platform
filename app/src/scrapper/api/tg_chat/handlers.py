import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from src.scrapper.api.schemas import ApiErrorResponse
from src.scrapper.repository.storage import InMemoryStorage

__all__ = ("router",)

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_storage(request: Request) -> InMemoryStorage:
    storage: InMemoryStorage = request.app.state.storage
    return storage


@router.post("/tg-chat/{chat_id}", status_code=status.HTTP_200_OK)
async def register_chat(chat_id: int, request: Request) -> JSONResponse:
    storage = _get_storage(request)
    registered = storage.register_chat(chat_id)
    if not registered:
        error = ApiErrorResponse(
            description="Chat already exists",
            code="409",
            exceptionName="ChatAlreadyExistsError",
            exceptionMessage=f"Chat {chat_id} is already registered",
        )
        return JSONResponse(status_code=409, content=error.model_dump())
    logger.info("Registered chat", extra={"chat_id": chat_id})
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.delete("/tg-chat/{chat_id}", status_code=status.HTTP_200_OK)
async def delete_chat(chat_id: int, request: Request) -> JSONResponse:
    storage = _get_storage(request)
    deleted = storage.delete_chat(chat_id)
    if not deleted:
        error = ApiErrorResponse(
            description="Chat not found",
            code="404",
            exceptionName="ChatNotFoundError",
            exceptionMessage=f"Chat {chat_id} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())
    logger.info("Deleted chat", extra={"chat_id": chat_id})
    return JSONResponse(status_code=200, content={"status": "ok"})
