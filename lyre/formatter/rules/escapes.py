"""R10: prose backslash escapes whose bare character cannot become markup (both profiles).

A screen reader such as TalkBack says "backslash" for every backslash it meets, and most
messaging apps show a Markdown escape (``2 \\* 3``) with its backslash. An escape loses its
backslash only when the bare character stands alone between two words, with a space or tab on
each side (``2 \\* 3`` becomes ``2 * 3``):

- A delimiter with whitespace on both sides is neither left- nor right-flanking, so it can never
  open or close emphasis or strikethrough, in Lyre's R1 or in CommonMark.
- A word character before it means the character is not at the start of a line or of a list
  item, quote or table cell, so it cannot start a heading, list, quote or rule.
- A word character after it keeps it out of an ATX heading's closing sequence and away from
  another escape or a protected span.

Characters that can pair or start markup anywhere on a line keep their backslash: backtick
(code spans), ``[`` and ``]`` (links), ``|`` (table cells), ``$`` (math in some apps) and ``\\``
itself (removing one backslash of two still leaves a backslash to hear). Escapes inside code,
URLs, link destinations and HTML tags are not escape tokens at this level, so they are never
seen here. The rule runs after every other inline rule, so the word on each side is the one the
output will show, and a second pass finds no escape left to judge differently.
"""

from __future__ import annotations

import re

from ..model import Options
from ..spans import ESCAPE_RE, OPEN
from . import register_inline_rule

# An escape placeholder, or a raw escape that an earlier rule exposed: removing the emoji between
# a lone backslash and ``)`` leaves ``\)``. The next pass protects it, so both get the same test.
_ESCAPE = re.compile("\ue000e\\d+\ue001|" + ESCAPE_RE.pattern)
_KEEP = frozenset("`[]|$\\")
_SPACE = " \t"


def _word(ch: str) -> bool:
    return ch.isalnum()


def _safe(text: str, start: int, end: int) -> bool:
    """True when the escape token at ``text[start:end]`` sits alone between two words."""
    if start < 2 or end + 1 >= len(text) or text[start - 1] not in _SPACE or text[end] not in _SPACE:
        return False
    # Each whitespace run is walked only by the escapes on either side of it: linear overall.
    i = start - 1
    while i >= 0 and text[i] in _SPACE:
        i -= 1
    j = end
    while j < len(text) and text[j] in _SPACE:
        j += 1
    return i >= 0 and j < len(text) and _word(text[i]) and _word(text[j])


def prose_escapes(text: str, opts: Options) -> str:
    if (OPEN + "e" not in text and "\\" not in text) or opts.span is None:
        return text
    span = opts.span

    def replace(match: re.Match) -> str:
        value = match.group(0) if match.group(0)[0] == "\\" else span(match.group(0))
        if value is None or len(value) != 2 or value[1] in _KEEP:
            return match.group(0)
        return value[1] if _safe(text, match.start(), match.end()) else match.group(0)

    return _ESCAPE.sub(replace, text)


# Last: after emphasis (50), drawing-only (80) and links (90), so the neighbours it checks are final.
register_inline_rule("prose-escapes", prose_escapes, order=95)
