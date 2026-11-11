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

# Emoji are matched by presentation, not by whole Unicode blocks, so symbols that share those
# blocks (music sharps and flats, stars, check marks, chess and alchemy signs) are never
# removed (ADR 0004). Characters that display as emoji by default always count; characters
# that are text by default count only with the emoji presentation selector U+FE0F. Status
# symbols always count, because models often omit the selector.
_PRESENTATION = (
    "\u231A\u231B\u23E9-\u23EC\u23F0\u23F3\u25FD\u25FE\u2614\u2615\u2648-\u2653\u267F\u2693\u26A1"
    "\u26AA\u26AB\u26BD\u26BE\u26C4\u26C5\u26CE\u26D4\u26EA\u26F2\u26F3\u26F5\u26FA\u26FD\u2705"
    "\u270A\u270B\u2728\u274C\u274E\u2753-\u2755\u2757\u2795-\u2797\u27B0\u27BF\u2B1B\u2B1C\u2B50"
    "\u2B55\U0001F004\U0001F0CF\U0001F18E\U0001F191-\U0001F19A\U0001F201\U0001F21A\U0001F22F"
    "\U0001F232-\U0001F236\U0001F238-\U0001F23A\U0001F250\U0001F251\U0001F300-\U0001F64F"
    "\U0001F680-\U0001F6FF\U0001F7E0-\U0001F7EB\U0001F7F0\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF"
    "\u2611\u2714\u2716\u26A0"  # status symbols, text by default
)
_TEXT_DEFAULT = (
    "\u00A9\u00AE\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9\u21AA\u2328\u23CF\u23ED-\u23EF"
    "\u23F1\u23F2\u23F8-\u23FA\u24C2\u25AA\u25AB\u25B6\u25C0\u25FB\u25FC\u2600-\u2604\u260E\u2618"
    "\u261D\u2620\u2622\u2623\u2626\u262A\u262E\u262F\u2638-\u263A\u2640\u2642\u265F\u2660\u2663"
    "\u2665\u2666\u2668\u267B\u267E\u2692\u2694-\u2697\u2699\u269B\u269C\u26A7\u26B0\u26B1\u26C8"
    "\u26CF\u26D1\u26D3\u26E9\u26F0\u26F1\u26F4\u26F7-\u26F9\u2702\u2708\u2709\u270C\u270D\u270F"
    "\u2712\u271D\u2721\u2733\u2734\u2744\u2747\u2763\u2764\u27A1\u2934\u2935\u2B05-\u2B07\u3030"
    "\u303D\u3297\u3299\U0001F170\U0001F171\U0001F17E\U0001F17F\U0001F202\U0001F237"
)
_MOD = "[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?[\U000E0020-\U000E007F]*"
_UNIT = (
    "(?:[#*0-9]\uFE0F?\u20E3"                      # keycap
    "|[\U0001F1E6-\U0001F1FF]{2}"                  # flag pair
    f"|[{_PRESENTATION}]{_MOD}"                     # emoji by default
    f"|[{_TEXT_DEFAULT}]\uFE0F{_MOD}"              # text by default, emoji with U+FE0F
    f"|[{_TEXT_DEFAULT}][\U0001F3FB-\U0001F3FF]{_MOD})"  # or with a skin tone (☝🏽)
)
# Inside a joiner sequence the parts may omit the selector (woman health worker, heart on fire).
_JOINED = f"(?:{_UNIT}|[{_TEXT_DEFAULT}]\uFE0F?{_MOD})"
# A joiner sequence may also start with a text-default part (heart on fire, U+2764 U+200D ...).
_SEQUENCE = f"(?:{_UNIT}|[{_TEXT_DEFAULT}]\uFE0F?{_MOD}(?=\u200D))(?:\u200D{_JOINED})*"
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
_DELIMITERS = "*_~"  # an emphasis delimiter touching the emoji must keep touching the text


def _opening_delimiter_before(left: str) -> bool:
    """``**`` directly before the emoji, itself after whitespace or line start: it opens emphasis."""
    body = left.rstrip(_DELIMITERS)
    return len(body) < len(left) and (not body or body[-1] in " \t")


def _closing_delimiter_after(right: str) -> bool:
    """``**`` directly after the emoji, itself before whitespace or line end: it closes emphasis."""
    body = right.lstrip(_DELIMITERS)
    return len(body) < len(right) and (not body or body[0] in " \t")


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
    tight_left = left_text.endswith(tuple(_NO_SPACE_AFTER)) or _opening_delimiter_before(left)
    tight_right = right_text.startswith(tuple(_NO_SPACE_BEFORE)) or _closing_delimiter_after(right)
    gap_left = bool(left.strip()) and bool(body or right_text) and not tight_left
    gap_right = bool(right_text) and bool(body) and not tight_right
    if not body:
        gap_right = False
        gap_left = gap_left and bool(right_text) and not tight_right
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
