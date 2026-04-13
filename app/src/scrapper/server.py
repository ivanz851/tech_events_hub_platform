import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from telethon import TelegramClient

from src.resilience.circuit_breaker import CircuitBreaker
from src.resilience.rate_limiter import RateLimitMiddleware
from src.scrapper.api import router
from src.scrapper.clients.bot import BotClient
from src.scrapper.db.engine import create_engine, create_session_factory
from src.scrapper.kafka.producer import KafkaProducerClient
from src.scrapper.notification.abstract import AbstractNotificationService
from src.scrapper.notification.fallback import FallbackNotificationService
from src.scrapper.notification.http import HttpNotificationService
from src.scrapper.notification.kafka_notification import KafkaNotificationService
from src.scrapper.repository.abstract import AbstractLinkRepository
from src.scrapper.repository.orm_repository import OrmLinkRepository
from src.scrapper.repository.sql_repository import SqlLinkRepository
from src.scrapper.scheduler import Scheduler
from src.scrapper.settings import AccessType, MessageTransport, ScrapperSettings
from src.scrapper.telegram_scrapper import TelegramChannelScrapper
from src.settings import TGBotSettings

logger = logging.getLogger(__name__)

_settings = ScrapperSettings()  # type: ignore[call-arg]


def _build_repository(settings: ScrapperSettings) -> AbstractLinkRepository:
    if settings.access_type == AccessType.ORM:
        engine = create_engine(settings.db_url)
        session_factory = create_session_factory(engine)
        return OrmLinkRepository(session_factory)
    dsn = settings.db_url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )
    return SqlLinkRepository(dsn)


def _build_bot_client(settings: ScrapperSettings) -> BotClient:
    cb = CircuitBreaker(
        sliding_window_size=settings.cb_sliding_window_size,
        min_calls=settings.cb_min_calls,
        failure_rate_threshold=settings.cb_failure_rate_threshold,
        wait_duration_seconds=settings.cb_wait_duration_seconds,
        permitted_calls_in_half_open=settings.cb_permitted_calls_in_half_open,
    )
    return BotClient(
        base_url=settings.bot_base_url,
        timeout_seconds=settings.http_timeout_seconds,
        retry_count=settings.retry_count,
        retry_backoff_seconds=settings.retry_backoff_seconds,
        retry_on_codes=set(settings.retry_on_codes),
        circuit_breaker=cb,
    )


def _build_notification(
    settings: ScrapperSettings,
    kafka_producer: KafkaProducerClient | None,
) -> AbstractNotificationService:
    http_service = HttpNotificationService(_build_bot_client(settings))
    if settings.message_transport == MessageTransport.KAFKA and kafka_producer is not None:
        kafka_service = KafkaNotificationService(kafka_producer, settings.kafka_updates_topic)
        return FallbackNotificationService(kafka_service, http_service)
    return http_service


@asynccontextmanager
async def default_lifespan(application: FastAPI) -> AsyncIterator[None]:
    scrapper_settings = ScrapperSettings()  # type: ignore[call-arg]
    bot_settings = TGBotSettings()  # type: ignore[call-arg]

    repository = _build_repository(scrapper_settings)

    kafka_producer: KafkaProducerClient | None = None
    if scrapper_settings.message_transport == MessageTransport.KAFKA:
        kafka_producer = KafkaProducerClient(scrapper_settings.kafka_bootstrap_servers)
        await kafka_producer.start()

    notification = _build_notification(scrapper_settings, kafka_producer)

    tg_client = TelegramClient(
        "scrapper_session",
        bot_settings.api_id,
        bot_settings.api_hash,
    )
    logger.info(
        "Starting Telegram user session for scrapper. "
        "If prompted, enter your phone number and the code from Telegram.",
    )
    await tg_client.start()

    tg_scrapper = TelegramChannelScrapper(tg_client)
    scheduler = Scheduler(
        repository=repository,
        notification=notification,
        tg_scrapper=tg_scrapper,
        interval_seconds=scrapper_settings.scheduler_interval_seconds,
        batch_size=scrapper_settings.batch_size,
        worker_count=scrapper_settings.worker_count,
    )

    application.state.repository = repository

    task = asyncio.create_task(scheduler.run())
    logger.info("Scrapper started")
    yield
    task.cancel()
    if kafka_producer is not None:
        await kafka_producer.stop()
    await tg_client.disconnect()
    logger.info("Scrapper stopped")


app = FastAPI(title="scrapper_app", lifespan=default_lifespan)
app.include_router(router=router)
app.add_middleware(RateLimitMiddleware, requests_per_minute=_settings.rate_limit_per_minute)


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    logger.info("Serving scrapper on port 8080")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level=os.getenv("LOGGING_LEVEL", "info").lower(),
    )
