"""R2: headings (plain profile only).

``# Results`` and Setext headings become ``Results.`` on their own line, with a blank line
before them when text directly precedes. ``full`` verbosity names the level. On the markdown
profile the rule steps aside and the client renders the heading.
"""

from __future__ import annotations

import re

from ..model import Block, Options
from . import InlineFn, register_block_rule

_ATX_TEXT = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)(.*?)(?:[ \t]+#+)?[ \t]*$")
_END_PUNCT = (".", "!", "?", ":")


def heading_text(block: Block) -> str:
    if block.meta.get("setext"):
        return " ".join(line.strip() for line in block.lines[:-1])  # every line above the underline
    m = _ATX_TEXT.match(block.lines[0])
    return m.group(1).strip() if m else block.lines[0].strip()


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
