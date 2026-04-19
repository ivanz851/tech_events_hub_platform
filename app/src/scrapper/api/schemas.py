from pydantic import BaseModel, Field

from src.scrapper.models import SubscriptionFilters

__all__ = (
    "AddLinkRequest",
    "RemoveLinkRequest",
    "LinkResponse",
    "ListLinksResponse",
    "ApiErrorResponse",
)


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exception_name: str = Field(default="", alias="exceptionName")
    exception_message: str = Field(default="", alias="exceptionMessage")
    stacktrace: list[str] = []


class AddLinkRequest(BaseModel):
    link: str
    filters: SubscriptionFilters | None = None


class RemoveLinkRequest(BaseModel):
    link: str


class LinkResponse(BaseModel):
    id: int
    url: str
    filters: SubscriptionFilters | None = None


class ListLinksResponse(BaseModel):
    links: list[LinkResponse]
    size: int
