import typing
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ("TGBotSettings",)


class TGBotSettings(BaseSettings):
    debug: bool = Field(default=False)

    api_id: int = Field(...)
    api_hash: str = Field(...)
    token: str = Field(...)

    scrapper_base_url: str = Field(default="http://localhost:8080")

    redis_url: str = Field(default="redis://localhost:6379")
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_updates_topic: str = Field(default="scrapper.updates")
    kafka_dlq_topic: str = Field(default="scrapper.updates.dlq")
    digest_time: str = Field(default="10:00")

    model_config: typing.ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore",
        frozen=True,
        case_sensitive=False,
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="BOT_",
    )
