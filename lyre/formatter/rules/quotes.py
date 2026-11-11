"""R9: blockquotes.

The core already formatted the quote's contents as a container. On the plain profile this rule
drops the ``>`` markers; at ``full`` verbosity it announces the quote on separate lines, so a
label inside the quote stays recognizable on the next pass. On the markdown profile it steps
aside and the core puts the markers back.
"""

from __future__ import annotations

from ..model import Block, Options
from . import InlineFn, register_block_rule


def blockquote(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    if opts.profile != "plain":
        return None
    inner = list(block.meta["inner_out"])
    while inner and not inner[0].strip():
        inner.pop(0)
    while inner and not inner[-1].strip():
        inner.pop()
    if not inner:
        return []
    if opts.verbosity == "full" and opts.latin:
        inner = ["Quote:", *inner, "End of quote."]
    return inner


register_block_rule("blockquote", blockquote)
