import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from src.metrics import detect_link_type, scrapper_active_links
from src.scrapper.api.schemas import (
    AddLinkRequest,
    ApiErrorResponse,
    LinkResponse,
    ListLinksResponse,
    RemoveLinkRequest,
)
from src.scrapper.repository.abstract import AbstractLinkRepository
from src.scrapper.strategies.abstract import LinkValidationError

if TYPE_CHECKING:
    from src.scrapper.strategies.factory import StrategyFactory

__all__ = ("router",)

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_repository(request: Request) -> AbstractLinkRepository:
    repository: AbstractLinkRepository = request.app.state.repository
    return repository


@router.get("/links", response_model=ListLinksResponse)
async def get_links(
    request: Request,
    tg_chat_id: int = Header(alias="Tg-Chat-Id"),
) -> JSONResponse:
    repository = _get_repository(request)
    if not await repository.chat_exists(tg_chat_id):
        error = ApiErrorResponse(
            description="Chat not found",
            code="404",
            exceptionName="ChatNotFoundError",
            exceptionMessage=f"Chat {tg_chat_id} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    records = await repository.get_links(tg_chat_id)
    links = [LinkResponse(id=r.id, url=r.url, tags=r.tags, filters=r.filters) for r in records]
    response = ListLinksResponse(links=links, size=len(links))
    return JSONResponse(status_code=200, content=response.model_dump())


@router.post("/links", status_code=status.HTTP_200_OK)
async def add_link(
    body: AddLinkRequest,
    request: Request,
    tg_chat_id: int = Header(alias="Tg-Chat-Id"),
) -> JSONResponse:
    repository = _get_repository(request)
    if not await repository.chat_exists(tg_chat_id):
        error = ApiErrorResponse(
            description="Chat not found",
            code="404",
            exceptionName="ChatNotFoundError",
            exceptionMessage=f"Chat {tg_chat_id} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    strategy_factory: StrategyFactory | None = getattr(request.app.state, "strategy_factory", None)
    if strategy_factory is not None:
        strategy = strategy_factory.get(body.link)
        try:
            await strategy.validate(body.link)
        except LinkValidationError as exc:
            error = ApiErrorResponse(
                description="Link validation failed",
                code="422",
                exceptionName="LinkValidationError",
                exceptionMessage=exc.reason,
            )
            return JSONResponse(status_code=422, content=error.model_dump())

    record = await repository.add_link(tg_chat_id, body.link, body.tags, body.filters)
    if record is None:
        error = ApiErrorResponse(
            description="Link already tracked",
            code="409",
            exceptionName="LinkAlreadyTrackedError",
            exceptionMessage=f"Link {body.link} is already tracked",
        )
        return JSONResponse(status_code=409, content=error.model_dump())

    logger.info("Added link", extra={"chat_id": tg_chat_id, "url": body.link})
    scrapper_active_links.labels(link_type=detect_link_type(body.link)).inc()
    link = LinkResponse(id=record.id, url=record.url, tags=record.tags, filters=record.filters)
    return JSONResponse(status_code=200, content=link.model_dump())


@router.delete("/links", status_code=status.HTTP_200_OK)
async def remove_link(
    body: RemoveLinkRequest,
    request: Request,
    tg_chat_id: int = Header(alias="Tg-Chat-Id"),
) -> JSONResponse:
    repository = _get_repository(request)
    if not await repository.chat_exists(tg_chat_id):
        error = ApiErrorResponse(
            description="Chat not found",
            code="404",
            exceptionName="ChatNotFoundError",
            exceptionMessage=f"Chat {tg_chat_id} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    record = await repository.remove_link(tg_chat_id, body.link)
    if record is None:
        error = ApiErrorResponse(
            description="Link not found",
            code="404",
            exceptionName="LinkNotFoundError",
            exceptionMessage=f"Link {body.link} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    logger.info("Removed link", extra={"chat_id": tg_chat_id, "url": body.link})
    scrapper_active_links.labels(link_type=detect_link_type(body.link)).dec()
    link = LinkResponse(id=record.id, url=record.url, tags=record.tags, filters=record.filters)
    return JSONResponse(status_code=200, content=link.model_dump())
