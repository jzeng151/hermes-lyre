"""R9: blockquotes.

The core already formatted the quote's contents as a container. On the plain profile this rule
drops the ``>`` markers; at ``full`` verbosity it announces the quote on separate lines, so a
label inside the quote stays recognizable on the next pass. On the markdown profile it steps
aside and the core puts the markers back.
"""

from __future__ import annotations

from ..model import Block, Options
from ..spans import FENCE_OPEN_RE, LIST_ITEM_RE
from . import InlineFn, register_block_rule


def blockquote(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    inner_out = block.meta["inner_out"]
    if opts.profile != "plain" or _keep_markers(inner_out) or (
            block.meta.get("prev_text") is not None and _holds_code_or_math(inner_out)):
        # The core keeps the markers. A quote can be what ends a list above; an exposed fence or
        # $$ block would not end it, so quoted code or math after other text stays quoted.
        return None
    inner = list(block.meta["inner_out"])
    while inner and not inner[0].strip():
        inner.pop(0)
    while inner and not inner[-1].strip():
        inner.pop()
    if not inner:
        return [""]  # a blank line keeps the blocks around the empty quote apart
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


def _holds_code_or_math(lines: list[str]) -> bool:
    return any(FENCE_OPEN_RE.match(line) or line.lstrip().startswith("$$") for line in lines)


def _keep_markers(lines: list[str]) -> bool:
    """True when removing the markers would change how the rest of the reply parses.

    An unclosed fence or ``$$`` would swallow what follows, and a list marker (one the list rule
    did not speak) would carry list context into the next block, such as indented code. Indented
    code is only code relative to its context: a list earlier in the reply, even after blank
    lines, would take it over as item text, so a quote holding indented code keeps its markers.
    """
    fence, math, prev_blank = None, False, True
    for line in lines:
        indented = line.startswith(("    ", "\t")) and bool(line.strip())
        if fence is None and not math and indented and prev_blank:
            return True
        prev_blank = not line.strip()
        body = line.strip()
        if fence is not None:
            if len(body) >= len(fence) and body == fence[0] * len(body):
                fence = None
            continue
        if math:
            math = "$$" not in line
            continue
        m = FENCE_OPEN_RE.match(line)
        if m and not (m.group(2)[0] == "`" and "`" in m.group(3)):
            if line[:1] in " \t":
                return True  # an indented fence's scope depends on list context outside the quote
            fence = m.group(2)
        elif body.startswith("$$"):
            math = not (len(body) >= 4 and body.endswith("$$"))
        elif LIST_ITEM_RE.match(line):
            return True
    return fence is not None or math


register_block_rule("blockquote", blockquote)
