import logging

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from src.scrapper.api.schemas import (
    AddLinkRequest,
    ApiErrorResponse,
    LinkResponse,
    ListLinksResponse,
    RemoveLinkRequest,
)
from src.scrapper.repository.storage import InMemoryStorage

__all__ = ("router",)

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_storage(request: Request) -> InMemoryStorage:
    storage: InMemoryStorage = request.app.state.storage
    return storage


@router.get("/links", response_model=ListLinksResponse)
async def get_links(
    request: Request,
    tg_chat_id: int = Header(alias="Tg-Chat-Id"),
) -> JSONResponse:
    storage = _get_storage(request)
    if not storage.chat_exists(tg_chat_id):
        error = ApiErrorResponse(
            description="Chat not found",
            code="404",
            exceptionName="ChatNotFoundError",
            exceptionMessage=f"Chat {tg_chat_id} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    records = storage.get_links(tg_chat_id)
    links = [LinkResponse(id=r.id, url=r.url, tags=r.tags, filters=r.filters) for r in records]
    response = ListLinksResponse(links=links, size=len(links))
    return JSONResponse(status_code=200, content=response.model_dump())


@router.post("/links", status_code=status.HTTP_200_OK)
async def add_link(
    body: AddLinkRequest,
    request: Request,
    tg_chat_id: int = Header(alias="Tg-Chat-Id"),
) -> JSONResponse:
    storage = _get_storage(request)
    if not storage.chat_exists(tg_chat_id):
        error = ApiErrorResponse(
            description="Chat not found",
            code="404",
            exceptionName="ChatNotFoundError",
            exceptionMessage=f"Chat {tg_chat_id} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    record = storage.add_link(tg_chat_id, body.link, body.tags, body.filters)
    if record is None:
        error = ApiErrorResponse(
            description="Link already tracked",
            code="409",
            exceptionName="LinkAlreadyTrackedError",
            exceptionMessage=f"Link {body.link} is already tracked",
        )
        return JSONResponse(status_code=409, content=error.model_dump())

    logger.info("Added link", extra={"chat_id": tg_chat_id, "url": body.link})
    link = LinkResponse(id=record.id, url=record.url, tags=record.tags, filters=record.filters)
    return JSONResponse(status_code=200, content=link.model_dump())


@router.delete("/links", status_code=status.HTTP_200_OK)
async def remove_link(
    body: RemoveLinkRequest,
    request: Request,
    tg_chat_id: int = Header(alias="Tg-Chat-Id"),
) -> JSONResponse:
    storage = _get_storage(request)
    if not storage.chat_exists(tg_chat_id):
        error = ApiErrorResponse(
            description="Chat not found",
            code="404",
            exceptionName="ChatNotFoundError",
            exceptionMessage=f"Chat {tg_chat_id} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    record = storage.remove_link(tg_chat_id, body.link)
    if record is None:
        error = ApiErrorResponse(
            description="Link not found",
            code="404",
            exceptionName="LinkNotFoundError",
            exceptionMessage=f"Link {body.link} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    logger.info("Removed link", extra={"chat_id": tg_chat_id, "url": body.link})
    link = LinkResponse(id=record.id, url=record.url, tags=record.tags, filters=record.filters)
    return JSONResponse(status_code=200, content=link.model_dump())
