from dataclasses import dataclass, field

__all__ = ("LinkRecord", "TrackedLink", "EventData")


@dataclass
class LinkRecord:
    id: int
    url: str
    tags: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)


@dataclass
class TrackedLink:
    link_id: int
    url: str
    chat_ids: list[int]


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
