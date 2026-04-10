from dataclasses import dataclass, field
from enum import Enum

__all__ = ("TrackStep", "TrackState", "TrackStateStore")


class TrackStep(Enum):
    WAITING_FOR_URL = "waiting_for_url"
    WAITING_FOR_FILTERS = "waiting_for_filters"
    WAITING_FOR_UNTRACK_URL = "waiting_for_untrack_url"


@dataclass
class TrackState:
    step: TrackStep
    url: str = ""
    tags: list[str] = field(default_factory=list)


class TrackStateStore:
    def __init__(self) -> None:
        self._store: dict[int, TrackState] = {}

    def get(self, chat_id: int) -> TrackState | None:
        return self._store.get(chat_id)

    def set(self, chat_id: int, state: TrackState) -> None:
        self._store[chat_id] = state

    def clear(self, chat_id: int) -> None:
        self._store.pop(chat_id, None)

    def has(self, chat_id: int) -> bool:
        return chat_id in self._store
