import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from telethon import TelegramClient

from src.scrapper.api import router
from src.scrapper.clients.bot import BotClient
from src.scrapper.repository.storage import InMemoryStorage
from src.scrapper.scheduler import Scheduler
from src.scrapper.settings import ScrapperSettings
from src.scrapper.telegram_scrapper import TelegramChannelScrapper
from src.settings import TGBotSettings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def default_lifespan(application: FastAPI) -> AsyncIterator[None]:
    scrapper_settings = ScrapperSettings()  # type: ignore[call-arg]
    bot_settings = TGBotSettings()  # type: ignore[call-arg]

    storage = InMemoryStorage()
    bot_client = BotClient(base_url=scrapper_settings.bot_base_url)

    tg_client = TelegramClient(
        "scrapper_session",
        bot_settings.api_id,
        bot_settings.api_hash,
    )
    logger.info(
        "Starting Telegram user session for scrapper. "
        "If prompted, enter your phone number and the code from Telegram."
    )
    await tg_client.start()

    tg_scrapper = TelegramChannelScrapper(tg_client)
    scheduler = Scheduler(
        storage,
        bot_client,
        tg_scrapper,
        scrapper_settings.scheduler_interval_seconds,
    )

    application.state.storage = storage

    task = asyncio.create_task(scheduler.run())
    logger.info("Scrapper started")
    yield
    task.cancel()
    await tg_client.disconnect()
    logger.info("Scrapper stopped")


app = FastAPI(title="scrapper_app", lifespan=default_lifespan)
app.include_router(router=router)


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
