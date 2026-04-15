import pytest
from prometheus_client import REGISTRY

from src.metrics import (
    bot_messages_total,
    detect_link_type,
    scrapper_active_links,
    scrapper_scrape_duration_seconds,
)


def _sample_value(name: str, labels: dict[str, str] | None = None) -> float:
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == name:
                if labels is None or all(sample.labels.get(k) == v for k, v in labels.items()):
                    return sample.value
    return 0.0


def test_bot_messages_total_exists_and_increments() -> None:
    before = _sample_value("bot_messages_total")
    bot_messages_total.inc()
    after = _sample_value("bot_messages_total")
    assert after == before + 1.0


def test_bot_messages_total_increments_by_n() -> None:
    before = _sample_value("bot_messages_total")
    bot_messages_total.inc(5)
    after = _sample_value("bot_messages_total")
    assert after == before + 5.0


def test_scrapper_active_links_exists_and_updates() -> None:
    scrapper_active_links.labels(link_type="telegram").set(0)
    scrapper_active_links.labels(link_type="telegram").inc()
    value = _sample_value("scrapper_active_links", {"link_type": "telegram"})
    assert value == 1.0


def test_scrapper_active_links_dec() -> None:
    scrapper_active_links.labels(link_type="web").set(3)
    scrapper_active_links.labels(link_type="web").dec()
    value = _sample_value("scrapper_active_links", {"link_type": "web"})
    assert value == 2.0


def test_scrapper_scrape_duration_seconds_exists_and_observes() -> None:
    before_count = _sample_value(
        "scrapper_scrape_duration_seconds_count",
        {"link_type": "telegram"},
    )
    scrapper_scrape_duration_seconds.labels(link_type="telegram").observe(0.5)
    after_count = _sample_value(
        "scrapper_scrape_duration_seconds_count",
        {"link_type": "telegram"},
    )
    assert after_count == before_count + 1.0


def test_scrapper_scrape_duration_seconds_sum_increases() -> None:
    before_sum = _sample_value("scrapper_scrape_duration_seconds_sum", {"link_type": "web"})
    scrapper_scrape_duration_seconds.labels(link_type="web").observe(2.5)
    after_sum = _sample_value("scrapper_scrape_duration_seconds_sum", {"link_type": "web"})
    assert after_sum == pytest.approx(before_sum + 2.5)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://t.me/durov", "telegram"),
        ("https://t.me/+abc123", "telegram"),
        ("https://www.t.me/channel", "telegram"),
        ("https://example.com/events", "web"),
        ("https://meetup.com/python", "web"),
        ("http://localhost:8080", "web"),
        ("not-a-url", "web"),
    ],
)
def test_detect_link_type(url: str, expected: str) -> None:
    assert detect_link_type(url) == expected
