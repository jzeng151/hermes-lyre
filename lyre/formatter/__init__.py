"""Speech formatter: turns a Hermes reply into text that reads well with a screen reader.

Pure functions with no I/O and no Hermes imports. Rule modules register into
``lyre.formatter.rules`` when imported here.
"""

from __future__ import annotations

from .core import format_for_speech
from .rules import code, decoration, emoji, emphasis, headings, links, lists, quotes, tables  # noqa: F401  (registers the rules)

__all__ = ["format_for_speech"]
