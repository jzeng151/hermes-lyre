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
from .emphasis import paired_delimiter_edges

# Emoji are matched by presentation, not by whole Unicode blocks, so symbols that share those
# blocks (music sharps and flats, stars, check marks, crosses, chess and alchemy signs) are
# never removed (ADR 0004). Characters that display as emoji by default always count; characters
# that are text by default count only with the emoji presentation selector U+FE0F. Status
# symbols always count, because models often omit the selector.
# Generated from Unicode 16.0 emoji-data.txt: Emoji_Presentation=Yes (always emoji) and Emoji=Yes
# without it (emoji only with U+FE0F). Keycap bases, regional indicators and skin tones are
# matched by their own patterns below. Refresh both tables when Unicode adds emoji.
_PRESENTATION = (
    "\u231A\u231B\u23E9-\u23EC\u23F0\u23F3\u25FD\u25FE\u2614\u2615\u2648-\u2653\u267F\u2693\u26A1"
    "\u26AA\u26AB\u26BD\u26BE\u26C4\u26C5\u26CE\u26D4\u26EA\u26F2\u26F3\u26F5\u26FA\u26FD\u2705"
    "\u270A\u270B\u2728\u274C\u274E\u2753-\u2755\u2757\u2795-\u2797\u27B0\u27BF\u2B1B\u2B1C\u2B50"
    "\u2B55\U0001F004\U0001F0CF\U0001F18E\U0001F191-\U0001F19A\U0001F201\U0001F21A\U0001F22F"
    "\U0001F232-\U0001F236\U0001F238-\U0001F23A\U0001F250\U0001F251\U0001F300-\U0001F320"
    "\U0001F32D-\U0001F335\U0001F337-\U0001F37C\U0001F37E-\U0001F393\U0001F3A0-\U0001F3CA"
    "\U0001F3CF-\U0001F3D3\U0001F3E0-\U0001F3F0\U0001F3F4\U0001F3F8-\U0001F3FA\U0001F400-\U0001F43E"
    "\U0001F440\U0001F442-\U0001F4FC\U0001F4FF-\U0001F53D\U0001F54B-\U0001F54E\U0001F550-\U0001F567"
    "\U0001F57A\U0001F595\U0001F596\U0001F5A4\U0001F5FB-\U0001F64F\U0001F680-\U0001F6C5\U0001F6CC"
    "\U0001F6D0-\U0001F6D2\U0001F6D5-\U0001F6D7\U0001F6DC-\U0001F6DF\U0001F6EB\U0001F6EC"
    "\U0001F6F4-\U0001F6FC\U0001F7E0-\U0001F7EB\U0001F7F0\U0001F90C-\U0001F93A\U0001F93C-\U0001F945"
    "\U0001F947-\U0001F9FF\U0001FA70-\U0001FA7C\U0001FA80-\U0001FA89\U0001FA8F-\U0001FAC6"
    "\U0001FACE-\U0001FADC\U0001FADF-\U0001FAE9\U0001FAF0-\U0001FAF8"
    "\u2611\u2714\u2716\u26A0"  # status symbols, text by default, matched bare
)
_TEXT_DEFAULT = (
    "\u00A9\u00AE\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9\u21AA\u2328\u23CF\u23ED-\u23EF"
    "\u23F1\u23F2\u23F8-\u23FA\u24C2\u25AA\u25AB\u25B6\u25C0\u25FB\u25FC\u2600-\u2604\u260E\u2611"
    "\u2618\u261D\u2620\u2622\u2623\u2626\u262A\u262E\u262F\u2638-\u263A\u2640\u2642\u265F\u2660"
    "\u2663\u2665\u2666\u2668\u267B\u267E\u2692\u2694-\u2697\u2699\u269B\u269C\u26A0\u26A7"
    "\u26B0\u26B1\u26C8\u26CF\u26D1\u26D3\u26E9\u26F0\u26F1\u26F4\u26F7-\u26F9\u2702\u2708\u2709"
    "\u270C\u270D\u270F\u2712\u2714\u2716\u271D\u2721\u2733\u2734\u2744\u2747\u2763\u2764\u27A1"
    "\u2934\u2935\u2B05-\u2B07\u3030\u303D\u3297\u3299\U0001F170\U0001F171\U0001F17E\U0001F17F"
    "\U0001F202\U0001F237\U0001F321\U0001F324-\U0001F32C\U0001F336\U0001F37D\U0001F396\U0001F397"
    "\U0001F399-\U0001F39B\U0001F39E\U0001F39F\U0001F3CB-\U0001F3CE\U0001F3D4-\U0001F3DF\U0001F3F3"
    "\U0001F3F5\U0001F3F7\U0001F43F\U0001F441\U0001F4FD\U0001F549\U0001F54A\U0001F56F\U0001F570"
    "\U0001F573-\U0001F579\U0001F587\U0001F58A-\U0001F58D\U0001F590\U0001F5A5\U0001F5A8"
    "\U0001F5B1\U0001F5B2\U0001F5BC\U0001F5C2-\U0001F5C4\U0001F5D1-\U0001F5D3\U0001F5DC-\U0001F5DE"
    "\U0001F5E1\U0001F5E3\U0001F5E8\U0001F5EF\U0001F5F3\U0001F5FA\U0001F6CB\U0001F6CD-\U0001F6CF"
    "\U0001F6E0-\U0001F6E5\U0001F6E9\U0001F6F0\U0001F6F3"
)
_MOD = "[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?[\U000E0020-\U000E007F]*"
_UNIT = (
    "(?:[#*0-9]\uFE0F?\u20E3"                      # keycap
    "|[\U0001F1E6-\U0001F1FF]{2}"                  # flag pair
    f"|[{_PRESENTATION}]{_MOD}"                     # emoji by default
    f"|[{_TEXT_DEFAULT}]\uFE0F{_MOD}"              # text by default, emoji with U+FE0F
    f"|[{_TEXT_DEFAULT}][\U0001F3FB-\U0001F3FF]{_MOD}"  # or with a skin tone (☝🏽)
    "|[\U0001F3FB-\U0001F3FF])"                     # standalone skin tone
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
_DELIMITERS = "*_~"
_BEFORE_OPENER = " \t([{\"'"  # what may sit before an opening delimiter: (**✅ Done**)
_AFTER_CLOSER = " \t.,;:!?)]}\"'"  # what may follow a closing delimiter: **Done 🎉**.  # an emphasis delimiter touching the emoji must keep touching the text


def _opening_delimiter_before(left: str) -> bool:
    """``**`` directly before the emoji, itself after whitespace or line start: it opens emphasis."""
    body = left.rstrip(_DELIMITERS)
    return len(body) < len(left) and (not body or body[-1] in _BEFORE_OPENER)


def _closing_delimiter_after(right: str, more_runs: bool = False) -> bool:
    """``**`` directly after the emoji, itself before whitespace or line end: it closes emphasis."""
    body = right.lstrip(_DELIMITERS)
    # A gap ending at the next emoji is not the end of the line.
    return len(body) < len(right) and (
        (not body and not more_runs) or (bool(body) and body[0] in _AFTER_CLOSER)
    )


def _label(sequence: str, opts: Options) -> str | None:
    if opts.emoji_policy == "remove":
        return None
    base = sequence.replace("\uFE0E", "").replace("\uFE0F", "")
    if base not in STATUS:
        return None
    return STATUS[base] if opts.latin else sequence


def _drop_emptied_wrapper(
    left: str, right: str, opening: bool, closing: bool, more_runs: bool,
) -> tuple[str, str]:
    """``**🎉**`` with the emoji removed leaves ``****``: drop the emptied delimiter pair too."""
    marks = left[len(left.rstrip(_DELIMITERS)):]
    closing_marks = right[:len(right) - len(right.lstrip(_DELIMITERS))]
    # Only an exact pair that wraps the emoji: the whole run on each side, mirrored, opening on
    # the left and closing on the right. ``*one*🎉**two**`` has a closer then an opener: kept.
    if (marks and closing_marks == marks[::-1]
            and (opening or _opening_delimiter_before(left))
            and (closing or _closing_delimiter_after(right, more_runs))):
        return left[:-len(marks)], right[len(marks):]
    return left, right


def _replace_run(
    run: str, left: str, right: str, opts: Options, opening: bool, closing: bool, more_runs: bool,
) -> tuple[str, str]:
    """Rewrite a run and its adjacent gaps without copying the remaining line."""
    labels = [label for m in SEQUENCE_RE.finditer(run)
              if (label := _label(m.group(0), opts))]
    if not labels:
        before = left, right
        left, right = _drop_emptied_wrapper(left, right, opening, closing, more_runs)
        if (left, right) != before:
            opening = closing = False
    left_text, right_text = left.rstrip(" \t"), right.lstrip(" \t")
    if not left.strip():
        left_text = left  # indentation before the first word is kept as written
    body = " ".join(labels)
    tight_left = opening or left_text.endswith(tuple(_NO_SPACE_AFTER)) or _opening_delimiter_before(left)
    tight_right = (closing or right_text.startswith(tuple(_NO_SPACE_BEFORE))
                   or _closing_delimiter_after(right, more_runs))
    has_right = bool(right_text) or more_runs
    gap_left = bool(left.strip()) and bool(body or has_right) and not tight_left
    gap_right = has_right and bool(body) and not tight_right
    if not body:
        gap_right = False
        gap_left = gap_left and has_right and not tight_right
    return left_text + (" " if gap_left else "") + body + (" " if gap_right else ""), right_text


def emoji(text: str, opts: Options) -> str:
    if text.isascii() or opts.emoji_policy == "keep" or not RUN_RE.search(text):
        return text
    matches = list(RUN_RE.finditer(text))
    # Keep original offsets even when earlier runs change length or empty a wrapper.
    openings, closings = paired_delimiter_edges(text)
    chunks = []
    left = text[:matches[0].start()]
    for index, match in enumerate(matches):
        more_runs = index + 1 < len(matches)
        next_start = matches[index + 1].start() if more_runs else len(text)
        right = text[match.end():next_start]
        head, left = _replace_run(
            match.group(0), left, right, opts,
            match.start() in openings, match.end() in closings, more_runs,
        )
        chunks.append(head)
    chunks.append(left)
    out = "".join(chunks)
    return out if out.strip() else ""


register_inline_rule("emoji", emoji, order=20)
