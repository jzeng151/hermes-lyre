"""R3: thematic breaks, box drawing and block elements (both profiles).

A thematic break is removed, or becomes one blank line when text sits directly above and below
it so the paragraphs stay apart. A line made only of box-drawing (U+2500 to U+257F) or block
element (U+2580 to U+259F) characters and spaces is removed. Lines mixing them with text, and
Braille Patterns, are never touched (spec R3).
"""

from __future__ import annotations

from ..model import Block, Options
from . import InlineFn, register_block_rule, register_inline_rule


def _is_drawing(ch: str) -> bool:
    return "\u2500" <= ch <= "\u259f"


def thematic_break(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    prev, nxt = block.meta.get("prev"), block.meta.get("next")
    if prev is not None and prev.strip() and nxt is not None and nxt.strip():
        return [""]
    return []


def drawing_only(text: str, opts: Options) -> str:
    body = text.strip()
    if body and _is_drawing(body[0]) and all(_is_drawing(ch) or ch in " \t" for ch in body):
        return ""
    return text


register_block_rule("rule", thematic_break)
# After emphasis (50) and emoji (20) removal, which can leave a line of only drawing characters.
register_inline_rule("drawing-only", drawing_only, order=80)
