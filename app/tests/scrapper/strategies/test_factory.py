from unittest.mock import MagicMock

from src.scrapper.strategies.factory import StrategyFactory
from src.scrapper.strategies.telegram import TelegramScrapperStrategy
from src.scrapper.strategies.web import WebScrapperStrategy


def _make_factory() -> StrategyFactory:
    tg_strategy = MagicMock(spec=TelegramScrapperStrategy)
    web_strategy = MagicMock(spec=WebScrapperStrategy)
    return StrategyFactory(tg_strategy=tg_strategy, web_strategy=web_strategy)


def test_factory_returns_telegram_strategy_for_tme_url() -> None:
    factory = _make_factory()
    result = factory.get("https://t.me/durov")
    assert result is factory.tg_strategy


def test_factory_returns_telegram_strategy_for_www_tme_url() -> None:
    factory = _make_factory()
    result = factory.get("https://www.t.me/channel")
    assert result is factory.tg_strategy


def test_factory_returns_web_strategy_for_http_url() -> None:
    factory = _make_factory()
    result = factory.get("https://example.com")
    assert result is factory.web_strategy


def test_factory_returns_web_strategy_for_unknown_url() -> None:
    factory = _make_factory()
    result = factory.get("https://habr.com/ru/events")
    assert result is factory.web_strategy
