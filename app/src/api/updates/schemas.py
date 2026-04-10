from pydantic import BaseModel, Field

__all__ = ("LinkUpdate", "ApiErrorResponse")


class LinkUpdate(BaseModel):
    id: int
    url: str
    description: str
    tg_chat_ids: list[int] = Field(alias="tgChatIds")


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exception_name: str = Field(default="", alias="exceptionName")
    exception_message: str = Field(default="", alias="exceptionMessage")
    stacktrace: list[str] = []
