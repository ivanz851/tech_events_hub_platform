from __future__ import annotations

import httpx

from src.scrapper.strategies.abstract import AbstractScrapperStrategy, LinkValidationError
from src.scrapper.telegram_scrapper import TelegramChannelScrapper, parse_channel_url

__all__ = ("TelegramScrapperStrategy",)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class TelegramScrapperStrategy(AbstractScrapperStrategy):
    def __init__(self, tg_scrapper: TelegramChannelScrapper, timeout_seconds: float = 5.0) -> None:
        self._tg_scrapper = tg_scrapper
        self._timeout = httpx.Timeout(timeout_seconds)

    async def validate(self, url: str) -> None:
        username, invite_hash = parse_channel_url(url)
        if not username and not invite_hash:
            raise LinkValidationError(url, "Invalid Telegram channel URL")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": _USER_AGENT},
                    follow_redirects=True,
                )
                if resp.status_code >= 400:  # noqa: PLR2004
                    raise LinkValidationError(url, f"HTTP {resp.status_code}")
        except httpx.RequestError as exc:
            raise LinkValidationError(url, str(exc)) from exc

    async def fetch_content(self, url: str) -> str:
        messages = await self._tg_scrapper.get_new_messages(url, min_id=0)
        return "\n".join(m.text for m in messages if m.text)
