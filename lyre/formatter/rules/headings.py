"""R2: headings (plain profile only).

``# Results`` and Setext headings become ``Results.`` on their own line, with a blank line
before them when text directly precedes. ``full`` verbosity names the level. On the markdown
profile the rule steps aside and the client renders the heading.
"""

from __future__ import annotations

import re

from ..model import Block, Options
from ..spans import TOKEN_RE
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
    if any(m.group(1) == "q" for line in block.lines for m in TOKEN_RE.finditer(line)):
        # An opaque container can end in code; punctuation would be appended inside it.
        return block.lines
    text = inline(heading_text(block)).strip()
    if not text:
        return []
    if not text.endswith(_END_PUNCT):
        text += "."
    if opts.verbosity == "full" and opts.latin:
        text = ("Heading: " if block.meta.get("level", 1) <= 2 else "Subheading: ") + text
    if text.startswith("$$") or _ATX_OPEN.match(text):
        # Exposed math can consume a later block; exposed ATX would be rewritten next pass.
        return block.lines
    prev = block.meta.get("prev")
    out = ["", text] if prev is not None and prev.strip() else [text]
    following = block.meta.get("next")
    if "`" in text and (following is None or following.strip()):
        # Unprotected backticks are unmatched within the heading. Once it becomes prose,
        # preserve its boundary even at container end: quote unwrapping can expose a later
        # paragraph or a full-verbosity label outside this recursive processing pass.
        out.append("")
    return out


register_block_rule("heading", headings)
