"""Work bounds for emoji matching and delimiter pairing."""

from time import perf_counter

import pytest

from lyre.formatter.model import Options
from lyre.formatter.rules import emoji, emphasis


@pytest.mark.parametrize("runs", [10, 100])
@pytest.mark.parametrize("marks", ["*", "~~"])
def test_delimiter_patterns_scan_original_line_once(monkeypatch, runs, marks):
    scans = []

    class CountScans:
        def __init__(self, pattern):
            self.pattern = pattern

        def finditer(self, text):
            scans.append(text)
            return self.pattern.finditer(text)

    monkeypatch.setattr(emphasis, "_EMPHASIS", [CountScans(p) for p in emphasis._EMPHASIS])
    monkeypatch.setattr(emphasis, "_STRIKE", CountScans(emphasis._STRIKE))
    text = f"{marks}🎉hi{marks} " * runs
    assert emoji.emoji(text, Options(profile="markdown")) == f"{marks}hi{marks} " * runs
    assert len(scans) == len(emphasis._EMPHASIS) + 1
    assert all(scanned is text for scanned in scans)


def test_many_emphasized_emoji_runs_stay_bounded():
    text = "*🎉hi* " * 2000
    start = perf_counter()
    out = emoji.emoji(text, Options(profile="markdown"))
    elapsed = perf_counter() - start
    assert out == "*hi* " * 2000
    assert elapsed < 1.0


def test_ascii_text_does_not_enter_the_unicode_emoji_matcher(monkeypatch):
    class NoSearch:
        def search(self, text):
            raise AssertionError("ASCII cannot contain an emoji sequence")

    monkeypatch.setattr(emoji, "RUN_RE", NoSearch())
    text = "Status: *1* #2 [docs](https://x.test) 1234567890"
    assert emoji.emoji(text, Options(profile="plain")) == text
