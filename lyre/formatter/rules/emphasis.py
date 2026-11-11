"""R1: emphasis and strikethrough markers.

Plain profile: paired ``**``, ``__``, ``*``, ``_`` and ``***`` markers are removed. Both profiles:
``~~gone~~`` becomes ``(removed: gone)``, except in mostly non-Latin replies, which get no
inserted English and keep the markers. Markers pair only on one line; escapes are protected
spans, so an escaped marker never pairs. Underscore markers also need whitespace, line end or
``,;:!?)`` after the closing marker, so file names like ``__init__.py`` keep their underscores
(ADR 0003).
"""

from __future__ import annotations

import re

from ..model import Options
from . import register_inline_rule

_EMPHASIS = [
    re.compile(r"\*\*\*(?=\S)([^*\n]+?)(?<=\S)\*\*\*"),
    re.compile(r"\*\*(?=\S)([^*\n]+?)(?<=\S)\*\*"),
    re.compile(r"(?<![\w.])__(?=\S)([^_\n]+?)(?<=\S)__(?=[\s,;:!?)]|$)"),
    re.compile(r"(?<![*\w])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![*\w])"),
    re.compile(r"(?<![\w.])_(?=[^\s_])([^_\n]+?)(?<=[^\s_])_(?=[\s,;:!?)]|$)"),
]
_STRIKE = re.compile(r"~~(?=\S)([^~\n]+?)(?<=\S)~~")


def emphasis(text: str, opts: Options) -> str:
    if opts.profile == "plain" and ("*" in text or "_" in text):
        # Nested emphasis (``**bold *italic* text**``) resolves inside out, so repeat until
        # stable; each round removes at least one marker pair, and the bound keeps it cheap.
        for _ in range(4):
            before = text
            for pattern in _EMPHASIS:
                text = pattern.sub(r"\1", text)
            if text == before:
                break
    if opts.latin and "~~" in text:
        text = _STRIKE.sub(r"(removed: \1)", text)
    return text


register_inline_rule("emphasis", emphasis, order=50)
