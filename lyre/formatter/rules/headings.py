"""R2: headings (plain profile only).

``# Results`` and Setext headings become ``Results.`` on their own line, with a blank line
before them when text directly precedes. ``full`` verbosity names the level. On the markdown
profile the rule steps aside and the client renders the heading.
"""

from __future__ import annotations

import re

from ..model import Block, Options
from . import InlineFn, register_block_rule

_ATX_OPEN = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)")
_END_PUNCT = (".", "!", "?", ":")


def heading_text(block: Block) -> str:
    if block.meta.get("setext"):
        return " ".join(line.strip() for line in block.lines[:-1])  # every line above the underline
    line = block.lines[0]
    m = _ATX_OPEN.match(line)
    if not m:
        return line.strip()
    return _strip_closing_hashes(line[m.end():].strip(" \t"))


def _strip_closing_hashes(text: str) -> str:
    """Drop an optional closing ``#`` run, which must follow a space or tab (linear scan)."""
    body = text.rstrip("#")
    if body == text:
        return text
    if not body:
        return ""
    return body.rstrip(" \t") if body[-1] in " \t" else text


def headings(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    if opts.profile != "plain":
        return None
    text = inline(heading_text(block)).strip()
    if not text:
        return []
    if not text.endswith(_END_PUNCT):
        text += "."
    if opts.verbosity == "full" and opts.latin:
        text = ("Heading: " if block.meta.get("level", 1) <= 2 else "Subheading: ") + text
    prev = block.meta.get("prev")
    return ["", text] if prev is not None and prev.strip() else [text]


register_block_rule("heading", headings)
