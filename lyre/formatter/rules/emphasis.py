"""R1: emphasis and strikethrough markers.

Plain profile: paired ``**``, ``__``, ``*``, ``_`` and ``***`` markers are removed. Both profiles:
``~~gone~~`` becomes ``(removed: gone)``, except in mostly non-Latin replies, which get no
inserted English and keep the markers. Markers pair only on one line; escapes are protected
spans, so an escaped marker never pairs. Single asterisks may pair inside a word but never next
to a digit (``2*3*4`` stays). Underscore markers also need whitespace, line end or
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
    re.compile(r"(?<![\w.])__(?=\S)([^_\n]+?)(?<=\S)__(?=[\s,;:!?)\]]|$)"),
    # Single asterisks may sit inside a word (``un*believ*able``, CJK text) but not next to a
    # digit, so arithmetic such as ``2*3*4`` keeps its operators.
    re.compile(r"(?<![*\d])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![*\d])"),
    re.compile(r"(?<![\w.])_(?=[^\s_])([^_\n]+?)(?<=[^\s_])_(?=[\s,;:!?)\]]|$)"),
]
_STRIKE = re.compile(r"~~(?=\S)([^~\n]+?)(?<=\S)~~")


def emphasis(text: str, opts: Options) -> str:
    # Strikethrough first: ``~~__x__~~`` must see ``)`` after the underscores in this same call.
    if opts.latin and "~~" in text:
        text = _STRIKE.sub(r"(removed: \1)", text)
    if opts.profile == "plain" and ("*" in text or "_" in text):
        # Nested emphasis (``**bold *italic* text**``) resolves inside out, so repeat until
        # stable; each round removes at least one marker pair, and the bound keeps it cheap.
        for _ in range(4):
            before = text
            for pattern in _EMPHASIS:
                text = pattern.sub(r"\1", text)
                # No later pattern or round can match once every delimiter is gone.
                if "*" not in text and "_" not in text:
                    return text
            if text == before:
                break
    return text


register_inline_rule("emphasis", emphasis, order=50)
