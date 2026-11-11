"""R3 thematic breaks, box drawing and decoration (task T3)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("text,expected", [
    ("A\n\n---\n\nB", "A\n\nB"),
    ("A\n\n* * *\n\nB", "A\n\nB"),
    ("A\n___\nB", "A\n\nB"),
    ("---\n\nB", "B"),
    ("Top\n\n┌──┐\n└──┘\n\nEnd", "Top\n\nEnd"),
    ("▀▀▀▀\ntext", "text"),
])
def test_rules_and_drawing_lines_removed(profile, text, expected):
    assert format_for_speech(text, profile=profile) == expected


@pytest.mark.parametrize("text", [
    "├── src/\n│   └── main.py",
    "⠓⠑⠇⠇⠕ means hello",
    "⠓⠑⠇⠇⠕",
    "```\n┌──┐\n---\n```",
    "    ┌──┐\n    └──┘",
])
def test_trees_braille_and_code_untouched(text):
    out = format_for_speech(text, profile="plain")
    assert text in out  # code blocks gain R7 labels around them; their lines never change


@pytest.mark.parametrize("text", ["A\n***\nB", "Top\n\n┌──┐\n\nEnd", "├── src/", "⠓⠑⠇⠇⠕"])
def test_idempotent(text):
    once = format_for_speech(text, profile="plain")
    assert format_for_speech(once, profile="plain") == once


def test_break_before_indented_code_is_kept():
    text = "- item\n***\n\n    **code**"
    once = format_for_speech(text, profile="plain")
    assert "***" in once.split("\n") and "    **code**" in once.split("\n")
    assert format_for_speech(once, profile="plain") == once


def test_removed_drawing_line_keeps_quotes_apart():
    once = format_for_speech("> ```\n──\n> ```\n> **literal**", profile="plain")
    assert "**literal**" in once
    assert format_for_speech(once, profile="plain") == once
