"""Avoid repeating expensive protection solely for root script detection."""

import pytest

from lyre.formatter import core


@pytest.mark.parametrize("text", [
    "Plain **prose** and `code`.",
    "> quoted `code`\n\nPlain prose.",
])
def test_script_detection_reuses_root_protection(monkeypatch, text):
    original = core._protect
    root_calls = 0

    def tracked(value, stash):
        nonlocal root_calls
        if value == text:
            root_calls += 1
        return original(value, stash)

    monkeypatch.setattr(core, "_protect", tracked)
    core.format_for_speech(text, profile="plain")
    assert root_calls == 1
