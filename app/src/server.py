import asyncio
import logging
import os
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api import router

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    logger.exception("Invalid request data: %s", exc)
    return await request_validation_exception_handler(request, exc)


@asynccontextmanager
async def default_lifespan(_application: FastAPI) -> AsyncIterator[None]:
    logger.debug("Running application lifespan ...")
    loop = asyncio.get_event_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=4))
    yield
    await loop.shutdown_default_executor()


app = FastAPI(
    title="telegram_bot_app",
    lifespan=default_lifespan,
)

app.exception_handler(RequestValidationError)(validation_exception_handler)
app.include_router(router=router, prefix="/api/v1")
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("serving app on port: %d", 7777)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7777,
        log_level=os.getenv("LOGGING_LEVEL", "info").lower(),
    )
