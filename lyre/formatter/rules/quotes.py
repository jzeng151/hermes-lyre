"""R9: blockquotes.

The core already formatted the quote's contents as a container. On the plain profile this rule
drops the ``>`` markers; at ``full`` verbosity it announces the quote on separate lines, so a
label inside the quote stays recognizable on the next pass. On the markdown profile it steps
aside and the core puts the markers back.
"""

from __future__ import annotations

from ..model import Block, Options
from ..spans import FENCE_OPEN_RE
from . import InlineFn, register_block_rule


def blockquote(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    if opts.profile != "plain" or _has_unclosed_fence(block.meta["inner_out"]):
        return None  # the core keeps the markers; an unclosed fence must stay inside the quote
    inner = list(block.meta["inner_out"])
    while inner and not inner[0].strip():
        inner.pop(0)
    while inner and not inner[-1].strip():
        inner.pop()
    if not inner:
        return []
    if opts.verbosity == "full" and opts.latin:
        # Indented code needs a blank line above it to stay code on the next pass.
        gap = [""] if inner[0][:4] == "    " or inner[0].startswith("\t") else []
        inner = ["Quote:", *gap, *inner, "End of quote."]
    prev = block.meta.get("prev")
    if prev is not None and prev.strip():
        # Keep the quote's contents a separate block from the text above, so a quoted
        # indented code block is still code on the next pass and prose is not merged.
        inner = ["", *inner]
    return inner


def _has_unclosed_fence(lines: list[str]) -> bool:
    fence = None
    for line in lines:
        body = line.strip()
        if fence is None:
            m = FENCE_OPEN_RE.match(line)
            if m and not (m.group(2)[0] == "`" and "`" in m.group(3)):
                fence = m.group(2)
        elif len(body) >= len(fence) and body == fence[0] * len(body):
            fence = None
    return fence is not None


register_block_rule("blockquote", blockquote)
