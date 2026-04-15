from __future__ import annotations
from urllib.parse import urlparse

from prometheus_client import Counter, Gauge, Histogram

__all__ = (
    "bot_messages_total",
    "scrapper_active_links",
    "scrapper_scrape_duration_seconds",
    "detect_link_type",
)

bot_messages_total: Counter = Counter(
    "bot_messages",
    "Total number of user Telegram messages received by the bot",
)

scrapper_active_links: Gauge = Gauge(
    "scrapper_active_links",
    "Number of active tracked links by type",
    ["link_type"],
)

scrapper_scrape_duration_seconds: Histogram = Histogram(
    "scrapper_scrape_duration_seconds",
    "Duration of a single URL scrape in seconds by link type",
    ["link_type"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)


def detect_link_type(url: str) -> str:
    try:
        parsed = urlparse(url)
    except ValueError:
        return "web"
    if parsed.netloc in ("t.me", "www.t.me"):
        return "telegram"
    return "web"
