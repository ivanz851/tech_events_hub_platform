import logging
from typing import Any
from urllib.parse import urlparse

from telethon import TelegramClient
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
from telethon.tl.types import ChatInviteAlready, Message

__all__ = ("TelegramChannelScrapper", "parse_channel_url")

logger = logging.getLogger(__name__)


def parse_channel_url(url: str) -> tuple[str | None, str | None]:
    """Returns (username, invite_hash).
    Public  channel → (username, None),  e.g. t.me/durov
    Private channel → (None, hash),      e.g. t.me/+gDai8jcIcKoyNjY6
    Unknown URL     → (None, None).
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return None, None
    if parsed.netloc not in ("t.me", "www.t.me"):
        return None, None
    path = parsed.path.strip("/")
    if not path:
        return None, None
    if path.startswith("+"):
        return None, path[1:]
    parts = path.split("/")
    username = parts[1] if len(parts) > 1 and parts[0] == "s" else parts[0]
    return username, None


def extract_channel_username(url: str) -> str | None:
    username, _ = parse_channel_url(url)
    return username


class TelegramChannelScrapper:
    def __init__(self, client: TelegramClient) -> None:
        self._client = client
        self._entities: dict[str, Any] = {}

    async def get_new_messages(self, url: str, min_id: int) -> list[Message]:
        """Return messages with id > min_id. Empty list on error or unknown URL."""
        username, invite_hash = parse_channel_url(url)
        if not username and not invite_hash:
            logger.warning("Unrecognised channel URL, skipping", extra={"url": url})
            return []
        try:
            entity = await self._resolve_entity(url, username, invite_hash)
            messages = await self._client.get_messages(entity, limit=50, min_id=min_id)
            return list(messages)
        except Exception as exc:
            logger.exception(
                "Failed to fetch messages",
                extra={"url": url, "error": str(exc)},
            )
            return []

    async def _resolve_entity(
        self,
        url: str,
        username: str | None,
        invite_hash: str | None,
    ) -> Any:  # noqa: ANN401
        if url in self._entities:
            return self._entities[url]

        if username:
            entity = await self._client.get_entity(username)
        else:
            entity = await self._resolve_private(invite_hash)  # type: ignore[arg-type]

        self._entities[url] = entity
        logger.info("Channel entity resolved and cached", extra={"url": url})
        return entity

    async def _resolve_private(self, invite_hash: str) -> Any:  # noqa: ANN401
        """Join (if needed) and return the channel entity for a private invite link."""
        result = await self._client(CheckChatInviteRequest(hash=invite_hash))
        if isinstance(result, ChatInviteAlready):
            return result.chat
        logger.info("Joining private channel via invite link")
        updates = await self._client(ImportChatInviteRequest(hash=invite_hash))
        return updates.chats[0]
