"""Bound emphasis work once no delimiters remain."""

from __future__ import annotations

import importlib

import pytest

from lyre.formatter.model import Options


@pytest.mark.parametrize("text,expected,bound", [
    ("***both*** word", "both word", 1),
    ("**bold** word", "bold word", 2),
    ("__bold__ word", "bold word", 3),
    ("*italic* word", "italic word", 4),
    ("_italic_ word", "italic word", 5),
])
def test_emphasis_stops_matching_after_last_delimiter(monkeypatch, text, expected, bound):
    module = importlib.import_module("lyre.formatter.rules.emphasis")
    calls = []

    class CountedPattern:
        def __init__(self, pattern):
            self.pattern = pattern

        def sub(self, replacement, value):
            calls.append(value)
            return self.pattern.sub(replacement, value)

    monkeypatch.setattr(module, "_EMPHASIS", [CountedPattern(pattern) for pattern in module._EMPHASIS])
    assert module.emphasis(text, Options(profile="plain")) == expected
    assert len(calls) <= bound
