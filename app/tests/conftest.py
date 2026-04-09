import asyncio
import os
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, Mock

os.environ.setdefault("BOT_API_ID", "123456")
os.environ.setdefault("BOT_API_HASH", "test")
os.environ.setdefault("BOT_TOKEN", "test")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from telethon import TelegramClient
from telethon.events import NewMessage

from src.api import router
from src.clients.scrapper import ScrapperClient
from src.scrapper.repository.storage import InMemoryStorage
from src.scrapper.server import default_lifespan as scrapper_lifespan
from src.scrapper.api import router as scrapper_router
from src.server import default_lifespan
from src.state.track import TrackStateStore


@pytest.fixture(scope="session")
def mock_event() -> Mock:
    event = Mock(spec=NewMessage.Event)
    event.input_chat = "test_chat"
    event.chat_id = 123456789
    event.message = "/chat_id"
    event.client = MagicMock(spec=TelegramClient)
    return event


@pytest.fixture
def mock_tg_event() -> Mock:
    event = AsyncMock(spec=NewMessage.Event)
    event.chat_id = 111222333
    event.raw_text = ""
    event.respond = AsyncMock()
    return event


@pytest.fixture
def scrapper_client_mock() -> Mock:
    return AsyncMock(spec=ScrapperClient)


@pytest.fixture
def state_store() -> TrackStateStore:
    return TrackStateStore()


@pytest.fixture(scope="session")
def fast_api_application() -> FastAPI:
    app = FastAPI(
        title="telegram_bot_app",
        lifespan=default_lifespan,
    )
    app.include_router(router=router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def test_client(fast_api_application: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(
        fast_api_application,
        backend_options={"loop_factory": asyncio.new_event_loop},
    ) as test_client:
        yield test_client


@pytest.fixture
def scrapper_storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def scrapper_app(scrapper_storage: InMemoryStorage) -> FastAPI:
    app = FastAPI(title="scrapper_app")
    app.state.storage = scrapper_storage
    app.include_router(router=scrapper_router)
    return app


@pytest.fixture
def scrapper_test_client(scrapper_app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(scrapper_app) as client:
        yield client
