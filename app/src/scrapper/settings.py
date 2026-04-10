import typing
from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ("ScrapperSettings", "AccessType")


class AccessType(str, Enum):
    ORM = "ORM"
    SQL = "SQL"


class ScrapperSettings(BaseSettings):
    debug: bool = Field(default=False)

    bot_base_url: str = Field(default="http://localhost:7777/api/v1")
    scheduler_interval_seconds: int = Field(default=10)

    db_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/scrapper",
    )
    access_type: AccessType = Field(default=AccessType.ORM)
    batch_size: int = Field(default=100)
    worker_count: int = Field(default=4)

    model_config: typing.ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore",
        frozen=True,
        case_sensitive=False,
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_prefix="SCRAPPER_",
    )
