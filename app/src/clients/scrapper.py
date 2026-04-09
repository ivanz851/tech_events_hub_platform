import logging
from dataclasses import dataclass
from http import HTTPStatus

import httpx

__all__ = ("LinkResponse", "ScrapperClient", "ScrapperClientError", "LinkAlreadyTrackedError")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LinkResponse:
    id: int
    url: str
    tags: list[str]
    filters: list[str]


class ScrapperClientError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class LinkAlreadyTrackedError(ScrapperClientError):
    pass


class ScrapperClient:
    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        self._base_url = base_url

    async def register_chat(self, chat_id: int) -> None:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post(f"/tg-chat/{chat_id}")
            if resp.status_code not in (HTTPStatus.OK, HTTPStatus.CONFLICT):
                raise ScrapperClientError(resp.status_code, resp.text)
        logger.info("Registered chat", extra={"chat_id": chat_id})

    async def delete_chat(self, chat_id: int) -> None:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.delete(f"/tg-chat/{chat_id}")
            if resp.status_code not in (HTTPStatus.OK, HTTPStatus.NOT_FOUND):
                raise ScrapperClientError(resp.status_code, resp.text)
        logger.info("Deleted chat", extra={"chat_id": chat_id})

    async def get_links(self, chat_id: int) -> list[LinkResponse]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.get("/links", headers={"Tg-Chat-Id": str(chat_id)})
            if resp.status_code != HTTPStatus.OK:
                raise ScrapperClientError(resp.status_code, resp.text)
            data = resp.json()
        return [
            LinkResponse(
                id=item["id"],
                url=item["url"],
                tags=item.get("tags", []),
                filters=item.get("filters", []),
            )
            for item in data.get("links", [])
        ]

    async def add_link(
        self,
        chat_id: int,
        link: str,
        tags: list[str],
        filters: list[str],
    ) -> LinkResponse:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post(
                "/links",
                headers={"Tg-Chat-Id": str(chat_id)},
                json={"link": link, "tags": tags, "filters": filters},
            )
            if resp.status_code == HTTPStatus.CONFLICT:
                raise LinkAlreadyTrackedError(HTTPStatus.CONFLICT, "Link already tracked")
            if resp.status_code != HTTPStatus.OK:
                raise ScrapperClientError(resp.status_code, resp.text)
            data = resp.json()
        logger.info("Added link", extra={"chat_id": chat_id, "url": link})
        return LinkResponse(
            id=data["id"],
            url=data["url"],
            tags=data.get("tags", []),
            filters=data.get("filters", []),
        )

    async def remove_link(self, chat_id: int, link: str) -> LinkResponse:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.request(
                "DELETE",
                "/links",
                headers={"Tg-Chat-Id": str(chat_id)},
                json={"link": link},
            )
            if resp.status_code == HTTPStatus.NOT_FOUND:
                raise ScrapperClientError(HTTPStatus.NOT_FOUND, "Link not found")
            if resp.status_code != HTTPStatus.OK:
                raise ScrapperClientError(resp.status_code, resp.text)
            data = resp.json()
        logger.info("Removed link", extra={"chat_id": chat_id, "url": link})
        return LinkResponse(
            id=data["id"],
            url=data["url"],
            tags=data.get("tags", []),
            filters=data.get("filters", []),
        )
