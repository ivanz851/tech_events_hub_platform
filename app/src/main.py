from __future__ import annotations
import asyncio
import logging

import redis.asyncio as aioredis
import uvicorn
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import ApiIdInvalidError
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

from src.bot.delivery import BotNotificationDelivery
from src.bot.digest_scheduler import DigestScheduler
from src.cache.digest_store import DigestStore
from src.cache.list_cache import ListCache
from src.cache.notify_mode_store import NotifyModeStore
from src.clients.scrapper import ScrapperClient
from src.handlers import (
    chat_id_cmd_handler,
    help_handler,
    make_list_handler,
    make_notify_handler,
    make_start_handler,
    make_track_command_handler,
    make_track_message_handler,
    make_untrack_handler,
    unknown_command_handler,
)
from src.kafka.consumer import KafkaUpdateConsumer
from src.resilience.circuit_breaker import CircuitBreaker
from src.server import app
from src.settings import TGBotSettings
from src.state.track import TrackStateStore

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


async def _register_commands(tg_client: TelegramClient) -> None:
    await tg_client(
        SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code="",
            commands=[
                BotCommand(command="start", description="Регистрация"),
                BotCommand(command="help", description="Список команд"),
                BotCommand(command="track", description="Отслеживать ресурс"),
                BotCommand(command="untrack", description="Прекратить отслеживание"),
                BotCommand(command="list", description="Список отслеживаемых ресурсов"),
                BotCommand(command="notify", description="Режим уведомлений"),
            ],
        ),
    )
    logger.info("Bot commands registered via setMyCommands")


def _register_handlers(
    client: TelegramClient,
    scrapper_client: ScrapperClient,
    state_store: TrackStateStore,
    list_cache: ListCache,
    notify_mode_store: NotifyModeStore,
) -> None:
    client.add_event_handler(
        chat_id_cmd_handler,
        events.NewMessage(pattern=r"^/chat_id(\s|$)"),
    )
    client.add_event_handler(
        make_start_handler(scrapper_client),
        events.NewMessage(pattern=r"^/start(\s|$)"),
    )
    client.add_event_handler(
        help_handler,
        events.NewMessage(pattern=r"^/help(\s|$)"),
    )
    client.add_event_handler(
        make_track_command_handler(state_store),
        events.NewMessage(pattern=r"^/track(\s|$)"),
    )
    client.add_event_handler(
        make_untrack_handler(scrapper_client, state_store, list_cache),
        events.NewMessage(pattern=r"^/untrack(\s|$)"),
    )
    client.add_event_handler(
        make_list_handler(scrapper_client, list_cache),
        events.NewMessage(pattern=r"^/list(\s|$)"),
    )
    client.add_event_handler(
        make_notify_handler(notify_mode_store),
        events.NewMessage(pattern=r"^/notify(\s|$)"),
    )
    client.add_event_handler(unknown_command_handler, events.NewMessage())
    client.add_event_handler(
        make_track_message_handler(state_store, scrapper_client, list_cache),
        events.NewMessage(),
    )


def _build_scrapper_client(settings: TGBotSettings) -> ScrapperClient:
    cb = CircuitBreaker(
        sliding_window_size=settings.cb_sliding_window_size,
        min_calls=settings.cb_min_calls,
        failure_rate_threshold=settings.cb_failure_rate_threshold,
        wait_duration_seconds=settings.cb_wait_duration_seconds,
        permitted_calls_in_half_open=settings.cb_permitted_calls_in_half_open,
    )
    return ScrapperClient(
        base_url=settings.scrapper_base_url,
        timeout_seconds=settings.http_timeout_seconds,
        retry_count=settings.retry_count,
        retry_backoff_seconds=settings.retry_backoff_seconds,
        retry_on_codes=set(settings.retry_on_codes),
        circuit_breaker=cb,
    )


async def main() -> None:
    settings = TGBotSettings()  # type: ignore[call-arg]
    scrapper_client = _build_scrapper_client(settings)
    state_store = TrackStateStore()

    redis_client: aioredis.Redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    list_cache = ListCache(redis_client)
    notify_mode_store = NotifyModeStore(redis_client)
    digest_store = DigestStore(redis_client)

    client = TelegramClient("bot_session", settings.api_id, settings.api_hash)
    _register_handlers(client, scrapper_client, state_store, list_cache, notify_mode_store)

    try:
        await client.start(bot_token=settings.token)
    except ApiIdInvalidError:
        logger.exception("Invalid Telegram API credentials")
        return

    delivery = BotNotificationDelivery(client, notify_mode_store, digest_store)
    app.tg_client = client  # type: ignore[attr-defined]
    app.delivery = delivery  # type: ignore[attr-defined]
    await _register_commands(client)
    logger.info("Bot started, waiting for messages")

    kafka_consumer = KafkaUpdateConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_updates_topic,
        dlq_topic=settings.kafka_dlq_topic,
        delivery=delivery,
    )
    digest_scheduler = DigestScheduler(digest_store, client, settings.digest_time)

    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=7777, log_level="warning")
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await asyncio.gather(
        client.run_until_disconnected(),
        uvicorn_server.serve(),
        kafka_consumer.run(),
        digest_scheduler.run(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logger.exception("Main loop raised error.", extra={"exc": exc})
