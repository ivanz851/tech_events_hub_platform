from pydantic import BaseModel

__all__ = ("LinkUpdate", "ApiErrorResponse")


class LinkUpdate(BaseModel):
    id: int
    url: str
    description: str
    tgChatIds: list[int]


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exceptionName: str = ""
    exceptionMessage: str = ""
    stacktrace: list[str] = []
