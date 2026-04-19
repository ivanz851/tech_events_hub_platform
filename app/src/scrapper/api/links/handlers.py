import logging
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from src.metrics import detect_link_type, scrapper_active_links
from src.scrapper.api.schemas import (
    AddLinkRequest,
    ApiErrorResponse,
    LinkResponse,
    ListLinksResponse,
    RemoveLinkRequest,
)
from src.scrapper.auth.dependencies import get_current_user
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
    user_id: UUID = Depends(get_current_user),
) -> JSONResponse:
    repository = _get_repository(request)
    records = await repository.get_links(user_id)
    links = [LinkResponse(id=r.id, url=r.url, filters=r.filters) for r in records]
    response = ListLinksResponse(links=links, size=len(links))
    return JSONResponse(status_code=200, content=response.model_dump())


@router.post("/links", status_code=status.HTTP_200_OK)
async def add_link(
    body: AddLinkRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user),
) -> JSONResponse:
    repository = _get_repository(request)

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

    record = await repository.add_link(user_id, body.link, body.filters)
    if record is None:
        error = ApiErrorResponse(
            description="Link already tracked",
            code="409",
            exceptionName="LinkAlreadyTrackedError",
            exceptionMessage=f"Link {body.link} is already tracked",
        )
        return JSONResponse(status_code=409, content=error.model_dump())

    logger.info("Added link", extra={"user_id": str(user_id), "url": body.link})
    scrapper_active_links.labels(link_type=detect_link_type(body.link)).inc()
    link = LinkResponse(id=record.id, url=record.url, filters=record.filters)
    return JSONResponse(status_code=200, content=link.model_dump())


@router.delete("/links", status_code=status.HTTP_200_OK)
async def remove_link(
    body: RemoveLinkRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user),
) -> JSONResponse:
    repository = _get_repository(request)
    record = await repository.remove_link(user_id, body.link)
    if record is None:
        error = ApiErrorResponse(
            description="Link not found",
            code="404",
            exceptionName="LinkNotFoundError",
            exceptionMessage=f"Link {body.link} not found",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    logger.info("Removed link", extra={"user_id": str(user_id), "url": body.link})
    scrapper_active_links.labels(link_type=detect_link_type(body.link)).dec()
    link = LinkResponse(id=record.id, url=record.url, filters=record.filters)
    return JSONResponse(status_code=200, content=link.model_dump())
