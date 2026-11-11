"""Speech formatter: turns a Hermes reply into text that reads well with a screen reader.

This module is a pure function with no I/O and no Hermes imports, so it can be unit-tested
on its own. The rules are added in later issues; until then the text passes through unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def format_for_speech(text: str, *, platform: str = "", settings: Mapping[str, Any] | None = None) -> str:
    """Return *text* rewritten for a screen reader on *platform*.

    Contract: never drops information, never changes code or URLs, idempotent,
    and returns the input unchanged when it cannot format it.
    """
    return text
