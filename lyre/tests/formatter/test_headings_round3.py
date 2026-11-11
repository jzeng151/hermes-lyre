"""Container and heading boundary regressions."""

import pytest

from lyre.formatter import format_for_speech
from lyre.formatter.rules import quotes


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_setext_after_opaque_quote_does_not_punctuate_code(profile, verbosity):
    text = "> quote\nlazy continuation\n>\n>     x = 1\n==="
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert ">     x = 1" in once.split("\n")
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_heading_with_heading_text_is_stable(profile, verbosity):
    text = "# # Title"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert "Title" in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_unwrapped_quote_keeps_trailing_paragraph_boundary(profile, verbosity):
    text = "> text `\n>\n`**code**`"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert "`**code**`" in once.split("\n")
    if profile == "plain":
        assert "text `\n\n" in once
        if verbosity == "full":
            assert "text `\n\nEnd of quote." in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


def test_leading_quote_blanks_require_linear_list_work(monkeypatch):
    shifted_slots = 0

    class WorkList(list):
        def pop(self, index=-1):
            nonlocal shifted_slots
            if index >= 0:
                shifted_slots += len(self) - index - 1
            return super().pop(index)

    monkeypatch.setattr(quotes, "list", WorkList, raising=False)
    text = ">\n" * 99_000 + "> text"
    assert len(text.encode("utf-8")) < 200_000
    assert format_for_speech(text, profile="plain") == "text"
    assert shifted_slots <= len(text)
