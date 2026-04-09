import pytest

from src.handlers.track import _is_valid_url


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
