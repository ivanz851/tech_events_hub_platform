import pytest

from src.scrapper.settings import ScrapperSettings


def test_playwright_timeout_seconds_default() -> None:
    settings = ScrapperSettings()  # type: ignore[call-arg]
    assert settings.playwright_timeout_seconds == 20.0


def test_playwright_timeout_seconds_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCRAPPER_PLAYWRIGHT_TIMEOUT_SECONDS", "30.0")
    settings = ScrapperSettings()  # type: ignore[call-arg]
    assert settings.playwright_timeout_seconds == 30.0
