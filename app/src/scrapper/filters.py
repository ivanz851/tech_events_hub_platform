from __future__ import annotations
import logging
import re
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.scrapper.models import EventData, SubscriptionFilters

__all__ = ("match_filters",)

logger = logging.getLogger(__name__)

_FREE_SUBSTRINGS = frozenset({"бесплатно", "free", "регистрация"})


def match_filters(event: EventData, filters: SubscriptionFilters | None) -> bool:
    if filters is None or _is_empty(filters):
        return True
    return (
        _city_matches(event, filters.city)
        and _date_matches(event, filters.date_from, filters.date_to)
        and _free_matches(event, filters.is_free)
        and _categories_match(event, filters.categories)
        and _format_matches(event, filters.format)
    )


def _is_empty(filters: SubscriptionFilters) -> bool:
    return (
        filters.city is None
        and filters.date_from is None
        and filters.date_to is None
        and filters.is_free is None
        and not filters.categories
        and filters.format is None
    )


def _city_matches(event: EventData, city: str | None) -> bool:
    if city is None:
        return True
    return city.lower() in (event.location or "").lower()


def _date_matches(
    event: EventData,
    from_date: date | None,
    to_date: date | None,
) -> bool:
    if from_date is None and to_date is None:
        return True
    return _check_date(event.event_date, from_date, to_date)


def _free_matches(event: EventData, is_free: bool | None) -> bool:
    if is_free is not True:
        return True
    price = (event.price or "").lower()
    tokens = set(re.split(r"\s+", price.strip()))
    return any(kw in price for kw in _FREE_SUBSTRINGS) or "0" in tokens


def _categories_match(event: EventData, categories: list[str]) -> bool:
    if not categories:
        return True
    event_tags_lower = {t.lower() for t in event.tags}
    return any(cat.lower() in event_tags_lower for cat in categories)


def _format_matches(event: EventData, fmt: str | None) -> bool:
    if fmt is None:
        return True
    return fmt.lower() == (event.format or "").lower()


def _check_date(
    event_date: str | None,
    from_date: date | None,
    to_date: date | None,
) -> bool:
    if not event_date:
        logger.warning("Event date is missing, date filter fails", extra={"event_date": event_date})
        return False
    try:
        parsed = datetime.strptime(event_date[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.warning("Cannot parse event date", extra={"event_date": event_date})
        return False
    if from_date is not None and parsed < from_date:
        return False
    return not (to_date is not None and parsed > to_date)
