import logging

import httpx

__all__ = ("BotClient", "BotClientError")

logger = logging.getLogger(__name__)


class BotClientError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class BotClient:
    def __init__(self, base_url: str = "http://localhost:7777/api/v1") -> None:
        self._base_url = base_url

    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        tg_chat_ids: list[int],
    ) -> None:
        payload = {
            "id": update_id,
            "url": url,
            "description": description,
            "tgChatIds": tg_chat_ids,
        }
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post("/updates", json=payload)
            if resp.status_code != 200:
                raise BotClientError(resp.status_code, resp.text)
        logger.info(
            "Sent update to bot",
            extra={"url": url, "chat_count": len(tg_chat_ids)},
        )
