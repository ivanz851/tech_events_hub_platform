from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

__all__ = (
    "LinkRecord",
    "TrackedLink",
    "EventData",
    "SubscriptionFilters",
    "SubscriberDTO",
    "RouteInfo",
    "UserProfile",
)


class SubscriptionFilters(BaseModel):
    city: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    is_free: bool | None = None
    categories: list[str] = []
    format: Literal["offline", "online", "hybrid"] | None = None


@dataclass
class SubscriberDTO:
    user_id: UUID
    filters: SubscriptionFilters | None


@dataclass
class RouteInfo:
    user_id: UUID
    tg_chat_id: int | None
    email: str | None
    notify_telegram: bool
    notify_email: bool


@dataclass
class UserProfile:
    user_id: UUID
    email: str | None
    providers: list[str]
    notify_telegram: bool
    notify_email: bool


@dataclass
class LinkRecord:
    id: int
    url: str
    filters: SubscriptionFilters | None = None


@dataclass
class TrackedLink:
    link_id: int
    url: str
    subscribers: list[SubscriberDTO]


@dataclass
class EventData:
    title: str | None = None
    event_date: str | None = None
    location: str | None = None
    price: str | None = None
    registration_url: str | None = None
    format: str | None = None
    event_type: str | None = None
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    organizer: str | None = None
