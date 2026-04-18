import pytest

from src.scrapper.llm.client import parse_llm_response


def test_parse_clean_json() -> None:
    raw = '{"is_event": true, "title": "PyCon 2025", "tags": ["python", "conference"]}'
    result = parse_llm_response(raw)
    assert result.is_event is True
    assert result.title == "PyCon 2025"
    assert result.tags == ["python", "conference"]


def test_parse_markdown_fenced_json() -> None:
    raw = '```json\n{"is_event": true, "title": "Hackathon"}\n```'
    result = parse_llm_response(raw)
    assert result.is_event is True
    assert result.title == "Hackathon"


def test_parse_dirty_json_with_leading_text() -> None:
    raw = 'Sure! Here is the result:\n{"is_event": false}\nHope that helps.'
    result = parse_llm_response(raw)
    assert result.is_event is False


def test_parse_is_event_false_minimal() -> None:
    raw = '{"is_event": false}'
    result = parse_llm_response(raw)
    assert result.is_event is False
    assert result.title is None
    assert result.tags == []


def test_parse_null_tags_coerced_to_empty_list() -> None:
    raw = '{"is_event": true, "tags": null}'
    result = parse_llm_response(raw)
    assert result.tags == []


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(Exception):
        parse_llm_response("this is not json at all")


def test_parse_full_event_fields() -> None:
    raw = (
        '{"is_event": true, "title": "DevFest", "event_date": "2025-11-01",'
        ' "location": "Moscow", "price": "free", "registration_url": "https://example.com",'
        ' "format": "offline", "event_type": "conference", "summary": "Big dev event",'
        ' "tags": ["android", "web"], "organizer": "Google"}'
    )
    result = parse_llm_response(raw)
    assert result.title == "DevFest"
    assert result.event_date == "2025-11-01"
    assert result.location == "Moscow"
    assert result.price == "free"
    assert result.registration_url == "https://example.com"
    assert result.format == "offline"
    assert result.event_type == "conference"
    assert result.summary == "Big dev event"
    assert result.tags == ["android", "web"]
    assert result.organizer == "Google"
