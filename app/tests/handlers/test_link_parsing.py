import pytest

from src.handlers.track import _is_valid_url
from src.scrapper.telegram_scrapper import parse_channel_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://t.me/somechannel", True),
        ("http://example.com/path?q=1", True),
        ("https://github.com/user/repo", True),
        ("not-a-url", False),
        ("ftp://bad-scheme.com", False),
        ("https://", False),
        ("", False),
        ("/relative/path", False),
        ("just text", False),
    ],
)
def test_is_valid_url(url: str, expected: bool) -> None:
    assert _is_valid_url(url) == expected


@pytest.mark.parametrize(
    ("url", "expected_username", "expected_hash"),
    [
        ("https://t.me/durov", "durov", None),
        ("https://t.me/some_channel", "some_channel", None),
        ("http://t.me/durov", "durov", None),
        ("https://www.t.me/durov", "durov", None),
        ("https://t.me/s/durov", "durov", None),
        ("https://t.me/s/some_channel", "some_channel", None),
        ("https://t.me/+gDai8jcIcKoyNjY6", None, "gDai8jcIcKoyNjY6"),
        ("https://example.com/channel", None, None),
        ("https://t.me/", None, None),
        ("not-a-url", None, None),
    ],
)
def test_parse_channel_url(
    url: str,
    expected_username: str | None,
    expected_hash: str | None,
) -> None:
    username, invite_hash = parse_channel_url(url)
    assert username == expected_username
    assert invite_hash == expected_hash
