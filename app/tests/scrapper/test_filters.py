from datetime import date

import pytest

from src.scrapper.filters import match_filters
from src.scrapper.models import EventData, SubscriptionFilters


def _event(**kwargs: object) -> EventData:
    defaults: dict[str, object] = {
        "title": "Test Event",
        "location": None,
        "event_date": None,
        "price": None,
        "tags": [],
        "format": None,
    }
    defaults.update(kwargs)
    return EventData(**defaults)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "filters",
    [
        None,
        SubscriptionFilters(),
        SubscriptionFilters(city=None, date_from=None, is_free=None, categories=[], format=None),
    ],
)
def test_no_filters_always_matches(filters: SubscriptionFilters | None) -> None:
    assert match_filters(_event(), filters) is True


def test_city_match_case_insensitive() -> None:
    f = SubscriptionFilters(city="moscow")
    assert match_filters(_event(location="Conference in Moscow, Russia"), f) is True


def test_city_match_substring() -> None:
    f = SubscriptionFilters(city="SPb")
    assert match_filters(_event(location="SPb Tech Hub"), f) is True


def test_city_no_match() -> None:
    f = SubscriptionFilters(city="Berlin")
    assert match_filters(_event(location="Moscow event"), f) is False


def test_city_event_location_none() -> None:
    f = SubscriptionFilters(city="Moscow")
    assert match_filters(_event(location=None), f) is False


def test_date_from_match() -> None:
    f = SubscriptionFilters(date_from=date(2025, 6, 1))
    assert match_filters(_event(event_date="2025-06-15 10:00"), f) is True


def test_date_from_boundary() -> None:
    f = SubscriptionFilters(date_from=date(2025, 6, 15))
    assert match_filters(_event(event_date="2025-06-15 10:00"), f) is True


def test_date_from_no_match() -> None:
    f = SubscriptionFilters(date_from=date(2025, 7, 1))
    assert match_filters(_event(event_date="2025-06-15 10:00"), f) is False


def test_date_to_match() -> None:
    f = SubscriptionFilters(date_to=date(2025, 12, 31))
    assert match_filters(_event(event_date="2025-06-15 10:00"), f) is True


def test_date_to_no_match() -> None:
    f = SubscriptionFilters(date_to=date(2025, 5, 31))
    assert match_filters(_event(event_date="2025-06-15 10:00"), f) is False


def test_date_range_match() -> None:
    f = SubscriptionFilters(date_from=date(2025, 6, 1), date_to=date(2025, 6, 30))
    assert match_filters(_event(event_date="2025-06-15"), f) is True


def test_date_range_outside() -> None:
    f = SubscriptionFilters(date_from=date(2025, 6, 1), date_to=date(2025, 6, 30))
    assert match_filters(_event(event_date="2025-07-01"), f) is False


def test_date_unparseable_returns_false() -> None:
    f = SubscriptionFilters(date_from=date(2025, 1, 1))
    assert match_filters(_event(event_date="not-a-date"), f) is False


def test_date_missing_returns_false() -> None:
    f = SubscriptionFilters(date_from=date(2025, 1, 1))
    assert match_filters(_event(event_date=None), f) is False


@pytest.mark.parametrize("price", ["бесплатно", "free", "0 руб", "регистрация"])
def test_is_free_match(price: str) -> None:
    f = SubscriptionFilters(is_free=True)
    assert match_filters(_event(price=price), f) is True


def test_is_free_no_match() -> None:
    f = SubscriptionFilters(is_free=True)
    assert match_filters(_event(price="5000 руб"), f) is False


def test_is_free_price_none() -> None:
    f = SubscriptionFilters(is_free=True)
    assert match_filters(_event(price=None), f) is False


def test_categories_match_case_insensitive() -> None:
    f = SubscriptionFilters(categories=["Python"])
    assert match_filters(_event(tags=["python", "ml"]), f) is True


def test_categories_any_match() -> None:
    f = SubscriptionFilters(categories=["Java", "Python"])
    assert match_filters(_event(tags=["python"]), f) is True


def test_categories_no_match() -> None:
    f = SubscriptionFilters(categories=["Java"])
    assert match_filters(_event(tags=["python", "ml"]), f) is False


def test_categories_empty_skips_check() -> None:
    f = SubscriptionFilters(categories=[])
    assert match_filters(_event(tags=[]), f) is True


def test_format_match_case_insensitive() -> None:
    f = SubscriptionFilters(format="offline")
    assert match_filters(_event(format="Offline"), f) is True


def test_format_no_match() -> None:
    f = SubscriptionFilters(format="online")
    assert match_filters(_event(format="offline"), f) is False


def test_format_event_none() -> None:
    f = SubscriptionFilters(format="offline")
    assert match_filters(_event(format=None), f) is False


def test_multiple_filters_all_match() -> None:
    f = SubscriptionFilters(city="Moscow", categories=["Python"], format="offline")
    event = _event(location="Moscow venue", tags=["python"], format="offline")
    assert match_filters(event, f) is True


def test_multiple_filters_one_fails() -> None:
    f = SubscriptionFilters(city="Moscow", categories=["Java"])
    event = _event(location="Moscow venue", tags=["python"])
    assert match_filters(event, f) is False
