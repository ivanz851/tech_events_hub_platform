from unittest.mock import AsyncMock

import pytest

from src.cache.list_cache import ListCache
from src.clients.scrapper import LinkResponse, ScrapperClient
from src.handlers.list_links import make_list_handler
from tests.bot.conftest import skip_without_docker

_LINKS = [
    LinkResponse(id=1, url="https://t.me/ch1", tags=["python"], filters=[]),
    LinkResponse(id=2, url="https://t.me/ch2", tags=[], filters=[]),
]


@pytest.mark.asyncio
async def test_cache_miss_fetches_from_scrapper_and_stores() -> None:
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()

    cache = ListCache(redis_mock)
    scrapper = AsyncMock(spec=ScrapperClient)
    scrapper.get_links = AsyncMock(return_value=_LINKS)

    result = await cache.get(123)
    assert result is None

    await scrapper.get_links(123)
    await cache.set(123, _LINKS)

    redis_mock.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_without_calling_scrapper() -> None:
    import json
    from dataclasses import asdict

    cached_json = json.dumps([asdict(link) for link in _LINKS])
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=cached_json)

    cache = ListCache(redis_mock)
    result = await cache.get(123)

    assert result is not None
    assert len(result) == 2
    assert result[0].url == "https://t.me/ch1"
    assert result[1].url == "https://t.me/ch2"


@pytest.mark.asyncio
async def test_cache_invalidated_on_track() -> None:
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()

    cache = ListCache(redis_mock)
    await cache.invalidate(123)

    redis_mock.delete.assert_called_once_with("list:123")


@pytest.mark.asyncio
async def test_list_handler_uses_cache_on_hit() -> None:
    import json
    from dataclasses import asdict

    mock_event = AsyncMock()
    mock_event.chat_id = 123
    mock_event.respond = AsyncMock()

    cached_json = json.dumps([asdict(link) for link in _LINKS])
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=cached_json)

    cache = ListCache(redis_mock)
    scrapper = AsyncMock(spec=ScrapperClient)

    handler = make_list_handler(scrapper, cache)

    with pytest.raises(Exception):
        await handler(mock_event)

    scrapper.get_links.assert_not_called()
    redis_mock.get.assert_called_once()


@skip_without_docker
@pytest.mark.asyncio
async def test_redis_cache_integration() -> None:
    from testcontainers.redis import RedisContainer

    with RedisContainer() as redis_container:
        import redis.asyncio as aioredis

        port = redis_container.get_exposed_port(6379)
        redis_client = aioredis.from_url(
            f"redis://localhost:{port}",
            decode_responses=True,
        )

        cache = ListCache(redis_client)

        assert await cache.get(999) is None

        await cache.set(999, _LINKS)

        cached = await cache.get(999)
        assert cached is not None
        assert len(cached) == 2
        assert cached[0].url == "https://t.me/ch1"

        await cache.invalidate(999)
        assert await cache.get(999) is None

        await redis_client.aclose()
