from pydantic import BaseModel

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
    exceptionName: str = ""
    exceptionMessage: str = ""
    stacktrace: list[str] = []


class AddLinkRequest(BaseModel):
    link: str
    tags: list[str] = []
    filters: list[str] = []


class RemoveLinkRequest(BaseModel):
    link: str


class LinkResponse(BaseModel):
    id: int
    url: str
    tags: list[str] = []
    filters: list[str] = []


class ListLinksResponse(BaseModel):
    links: list[LinkResponse]
    size: int
