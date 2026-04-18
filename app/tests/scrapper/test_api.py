from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def chat_id() -> int:
    return 42


def test_register_chat(scrapper_test_client: TestClient, chat_id: int) -> None:
    resp = scrapper_test_client.post(f"/tg-chat/{chat_id}")
    assert resp.status_code == HTTPStatus.OK


def test_register_chat_duplicate_returns_409(
    scrapper_test_client: TestClient,
    chat_id: int,
) -> None:
    scrapper_test_client.post(f"/tg-chat/{chat_id}")
    resp = scrapper_test_client.post(f"/tg-chat/{chat_id}")
    assert resp.status_code == HTTPStatus.CONFLICT


def test_delete_chat(scrapper_test_client: TestClient, chat_id: int) -> None:
    scrapper_test_client.post(f"/tg-chat/{chat_id}")
    resp = scrapper_test_client.delete(f"/tg-chat/{chat_id}")
    assert resp.status_code == HTTPStatus.OK


def test_delete_nonexistent_chat_returns_404(scrapper_test_client: TestClient) -> None:
    resp = scrapper_test_client.delete("/tg-chat/9999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_add_link(scrapper_test_client: TestClient, chat_id: int) -> None:
    scrapper_test_client.post(f"/tg-chat/{chat_id}")
    resp = scrapper_test_client.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://t.me/ch", "tags": ["py"], "filters": []},
    )
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["url"] == "https://t.me/ch"
    assert data["tags"] == ["py"]


def test_add_link_duplicate_returns_409(scrapper_test_client: TestClient, chat_id: int) -> None:
    scrapper_test_client.post(f"/tg-chat/{chat_id}")
    scrapper_test_client.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://t.me/ch", "tags": [], "filters": []},
    )
    resp = scrapper_test_client.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://t.me/ch", "tags": [], "filters": []},
    )
    assert resp.status_code == HTTPStatus.CONFLICT


def test_add_link_for_new_tg_chat_auto_creates_user(scrapper_test_client: TestClient) -> None:
    resp = scrapper_test_client.post(
        "/links",
        headers={"Tg-Chat-Id": "9999"},
        json={"link": "https://t.me/ch", "tags": [], "filters": []},
    )
    assert resp.status_code == HTTPStatus.OK


def test_get_links(scrapper_test_client: TestClient, chat_id: int) -> None:
    scrapper_test_client.post(f"/tg-chat/{chat_id}")
    scrapper_test_client.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://t.me/ch1", "tags": [], "filters": []},
    )
    scrapper_test_client.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://t.me/ch2", "tags": ["py"], "filters": []},
    )
    resp = scrapper_test_client.get("/links", headers={"Tg-Chat-Id": str(chat_id)})
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["size"] == 2


def test_remove_link(scrapper_test_client: TestClient, chat_id: int) -> None:
    scrapper_test_client.post(f"/tg-chat/{chat_id}")
    scrapper_test_client.post(
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://t.me/ch", "tags": [], "filters": []},
    )
    resp = scrapper_test_client.request(
        "DELETE",
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://t.me/ch"},
    )
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["url"] == "https://t.me/ch"


def test_remove_nonexistent_link_returns_404(
    scrapper_test_client: TestClient,
    chat_id: int,
) -> None:
    scrapper_test_client.post(f"/tg-chat/{chat_id}")
    resp = scrapper_test_client.request(
        "DELETE",
        "/links",
        headers={"Tg-Chat-Id": str(chat_id)},
        json={"link": "https://t.me/nope"},
    )
    assert resp.status_code == HTTPStatus.NOT_FOUND
