import typing
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ("ScrapperSettings",)


class ScrapperSettings(BaseSettings):
    debug: bool = Field(default=False)

    bot_base_url: str = Field(default="http://localhost:7777/api/v1")
    scheduler_interval_seconds: int = Field(default=10)

    model_config: typing.ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore",
        frozen=True,
        case_sensitive=False,
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_prefix="SCRAPPER_",
    )
