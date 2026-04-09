from pydantic import BaseModel

__all__ = ("LinkUpdate", "ApiErrorResponse")


class LinkUpdate(BaseModel):
    id: int
    url: str
    description: str
    tgChatIds: list[int]  # noqa: N815


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exceptionName: str = ""  # noqa: N815
    exceptionMessage: str = ""  # noqa: N815
    stacktrace: list[str] = []
