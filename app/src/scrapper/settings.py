import typing
from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ("ScrapperSettings", "AccessType", "MessageTransport")


class AccessType(str, Enum):
    ORM = "ORM"
    SQL = "SQL"


class MessageTransport(str, Enum):
    HTTP = "HTTP"
    KAFKA = "KAFKA"


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

    message_transport: MessageTransport = Field(default=MessageTransport.HTTP)
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_updates_topic: str = Field(default="scrapper.updates")
    kafka_dlq_topic: str = Field(default="scrapper.updates.dlq")

    http_timeout_seconds: float = Field(default=5.0)
    retry_count: int = Field(default=3)
    retry_backoff_seconds: float = Field(default=1.0)
    retry_on_codes: list[int] = Field(default=[502, 503, 429])
    rate_limit_per_minute: int = Field(default=60)
    cb_sliding_window_size: int = Field(default=1)
    cb_min_calls: int = Field(default=1)
    cb_failure_rate_threshold: float = Field(default=100.0)
    cb_wait_duration_seconds: float = Field(default=1.0)
    cb_permitted_calls_in_half_open: int = Field(default=1)

    @field_validator("retry_on_codes", mode="before")
    @classmethod
    def _parse_retry_codes(cls, v: object) -> list[int]:
        if isinstance(v, str):
            return [int(c.strip()) for c in v.split(",") if c.strip()]
        if isinstance(v, list):
            return [int(c) for c in v]
        return []

    model_config: typing.ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore",
        frozen=True,
        case_sensitive=False,
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_prefix="SCRAPPER_",
    )
