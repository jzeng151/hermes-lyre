"""R4: emoji (both profiles).

Each emoji sequence (base plus variation selector, skin tone, tag characters and zero-width
joiner parts; keycaps; flag pairs) is one unit, so no orphan code point is left. A run of
emoji separated only by spaces becomes the status words it contains, or disappears. Spacing is
only touched next to a run. Mostly non-Latin replies keep their status emoji instead of words.
"""

from __future__ import annotations

import re

from ..model import Options
from . import register_inline_rule

# Ranges match core's opt-in WhatsApp plain-output formatter, plus the emoji-presentation
# symbols outside them (watch, hourglass, media keys, star, circles, squares).
_BASE = (
    "\U0001F000-\U0001FAFF\u2600-\u27BF\u231A\u231B\u2328\u23CF\u23E9-\u23F3\u23F8-\u23FA"
    "\u2B05-\u2B07\u2B1B\u2B1C\u2B50\u2B55\u2934\u2935\u3030\u303D\u3297\u3299"
)
_MOD = "[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?[\U000E0020-\U000E007F]*"
_UNIT = (
    "(?:[#*0-9]\uFE0F?\u20E3"                       # keycap
    "|[\U0001F1E6-\U0001F1FF]{2}"                   # flag pair
    f"|[{_BASE}]{_MOD}"                             # pictograph
    "|[\u00A9\u00AE\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9\u21AA\u25AA\u25AB\u25B6\u25C0"
    "\u25FB-\u25FE]\uFE0F)"                         # text symbols only with emoji presentation
)
_SEQUENCE = f"{_UNIT}(?:\u200D{_UNIT})*"
SEQUENCE_RE = re.compile(_SEQUENCE)
RUN_RE = re.compile(f"{_SEQUENCE}(?:[ \t]*{_SEQUENCE})*")

STATUS = {
    "\u2705": "(done)", "\u2714": "(done)", "\u2611": "(done)",
    "\u274C": "(failed)", "\u2716": "(failed)", "\U0001F6AB": "(failed)",
    "\u26A0": "(warning)",
    "\U0001F534": "(red)", "\U0001F7E1": "(yellow)", "\U0001F7E2": "(green)",
    "\u23F3": "(pending)",
}
_NO_SPACE_BEFORE = ".,;:!?)]}"
_NO_SPACE_AFTER = "([{"


def _label(sequence: str, opts: Options) -> str | None:
    if opts.emoji_policy == "remove":
        return None
    base = sequence.replace("\uFE0E", "").replace("\uFE0F", "")
    if base not in STATUS:
        return None
    return STATUS[base] if opts.latin else sequence


def _replace_run(line: str, start: int, end: int, opts: Options) -> tuple[str, str]:
    """Return (new text for the run including spacing, rest of line)."""
    labels = [label for m in SEQUENCE_RE.finditer(line, start, end)
              if (label := _label(m.group(0), opts))]
    left, right = line[:start], line[end:]
    left_text, right_text = left.rstrip(" \t"), right.lstrip(" \t")
    if not left.strip():
        left_text = left  # indentation before the first word is kept as written
    body = " ".join(labels)
    gap_left = bool(left.strip()) and bool(body or right_text) and not left_text.endswith(tuple(_NO_SPACE_AFTER))
    gap_right = bool(right_text) and bool(body) and not right_text.startswith(tuple(_NO_SPACE_BEFORE))
    if not body:
        gap_right = False
        gap_left = gap_left and bool(right_text) and not right_text.startswith(tuple(_NO_SPACE_BEFORE))
    return left_text + (" " if gap_left else "") + body + (" " if gap_right else ""), right_text


def emoji(text: str, opts: Options) -> str:
    if opts.emoji_policy == "keep" or not RUN_RE.search(text):
        return text
    out = ""
    rest = text
    while True:
        m = RUN_RE.search(rest)
        if not m:
            break
        head, rest = _replace_run(rest, m.start(), m.end(), opts)
        out += head
    out += rest
    return out if out.strip() else ""


register_inline_rule("emoji", emoji, order=20)
