import asyncio
import logging

import uvicorn
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import ApiIdInvalidError
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

from src.clients.scrapper import ScrapperClient
from src.handlers import (
    chat_id_cmd_handler,
    help_handler,
    make_list_handler,
    make_start_handler,
    make_track_command_handler,
    make_track_message_handler,
    make_untrack_handler,
    unknown_command_handler,
)
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
            ],
        )
    )
    logger.info("Bot commands registered via setMyCommands")


def _register_handlers(
    client: TelegramClient,
    scrapper_client: ScrapperClient,
    state_store: TrackStateStore,
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
        make_untrack_handler(scrapper_client),
        events.NewMessage(pattern=r"^/untrack(\s|$)"),
    )
    client.add_event_handler(
        make_list_handler(scrapper_client),
        events.NewMessage(pattern=r"^/list(\s|$)"),
    )
    client.add_event_handler(unknown_command_handler, events.NewMessage())
    client.add_event_handler(
        make_track_message_handler(state_store, scrapper_client),
        events.NewMessage(),
    )


async def main() -> None:
    settings = TGBotSettings()  # type: ignore[call-arg]
    scrapper_client = ScrapperClient(base_url=settings.scrapper_base_url)
    state_store = TrackStateStore()

    client = TelegramClient("bot_session", settings.api_id, settings.api_hash)
    _register_handlers(client, scrapper_client, state_store)

    try:
        await client.start(bot_token=settings.token)
    except ApiIdInvalidError:
        logger.error("Invalid Telegram API credentials")
        return

    app.tg_client = client  # type: ignore[attr-defined]
    await _register_commands(client)
    logger.info("Bot started, waiting for messages")

    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=7777, log_level="warning")
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await asyncio.gather(
        client.run_until_disconnected(),
        uvicorn_server.serve(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logger.exception("Main loop raised error.", extra={"exc": exc})
