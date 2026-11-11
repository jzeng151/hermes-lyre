"""Work bounds for emoji matching on ASCII-only text."""

from lyre.formatter.model import Options
from lyre.formatter.rules import emoji


def test_ascii_text_does_not_enter_the_unicode_emoji_matcher(monkeypatch):
    class NoSearch:
        def search(self, text):
            raise AssertionError("ASCII cannot contain an emoji sequence")

    monkeypatch.setattr(emoji, "RUN_RE", NoSearch())
    text = "Status: *1* #2 [docs](https://x.test) 1234567890"
    assert emoji.emoji(text, Options(profile="plain")) == text
