"""R6: tables read as sentences (both profiles).

``Table, 2 rows, 3 columns: Name, Price, Stock.`` then one ``Row N:`` sentence per row that names
each column, then ``End of table.`` Every cell is kept; empty cells say ``blank``. Malformed or
oversized tables, and tables in mostly non-Latin replies, pass through byte-identical.
"""

from __future__ import annotations

import re
from dataclasses import replace

from ..model import Block, Options
from ..spans import TOKEN_RE, Stash, protect_code_spans, protect_inline
from . import InlineFn, inline_rules, register_block_rule

MAX_ROWS = 50
MAX_COLUMNS = 10
MAX_CELL = 500
_END_PUNCT = (".", "!", "?")
_PROTECTED_TARGET_RE = re.compile(r"\]\(" + TOKEN_RE.pattern + r"\)")
_REFERENCE_RE = re.compile(r"^ {0,3}\[[^\]\n]+\]:")


def split_row(line: str) -> list[str]:
    """Cells of one row. Escaped pipes are protected tokens, so splitting on ``|`` is safe."""
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") else body
    return [cell.strip() for cell in body.split("|")]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _sentence(text: str) -> str:
    return text if text.endswith(_END_PUNCT) else text + "."


def _original(cell: str, block: Block) -> str:
    """The cell as written, with protected spans (and spans nested in them) expanded."""
    span = block.meta.get("span")
    if not span:
        return cell
    for _ in range(8):  # nesting is shallow; the bound only guards against a bad token
        expanded = TOKEN_RE.sub(lambda m: span(m.group(0)) or m.group(0), cell)
        if expanded == cell:
            break
        cell = expanded
    return cell


def _unsafe_cell(cell: str, block: Block) -> bool:
    # Recheck restored text before link targets can hide unmatched code delimiters. In prose,
    # those delimiters could capture a protected code span in another row on the next pass.
    restored = _original(cell, block)
    # Protection can only expose these hazards if their delimiters occur in the original.
    # Ordinary cells need no second stash/protection pipeline; the complete emitted prose
    # is still independently restored and validated below, including cross-cell pairing.
    if not ("`" in restored or "<" in restored or "](" in restored or "$$" in restored
            or _REFERENCE_RE.match(restored)):
        return False
    stash = Stash()
    text = protect_code_spans([restored], stash, lambda line: False)[0]
    if "`" in text:
        return True
    # Complete tags, code, escapes and destinations are safe. An exposed '<' may instead
    # acquire a closing '>' from a repeated column label, creating a multiline HTML span.
    text = protect_inline(text, stash)
    # Paired math is protected above. Leftover $$ could pair across cells in prose,
    # changing which emphasis is protected on the next pass (including longer $ runs).
    # Math is recognized before escapes, so an escaped first dollar still counts.
    math_text = TOKEN_RE.sub(
        lambda m: (stash.value_of(m.group(0)) or m.group(0)) if m.group(1) == "e" else m.group(0), text)
    if "$$" in math_text:
        return True
    # Reference destinations depend on a line-start anchor, which prose cannot retain.
    # Keep both empty definitions and complete ones whose protection would be lost.
    if _REFERENCE_RE.match(text):
        return True
    # Complete targets keep their ](token) wrapper. Remove it before checking for an
    # incomplete opener that could acquire its closing ')' from another cell or row.
    exposed = TOKEN_RE.sub("", _PROTECTED_TARGET_RE.sub("", text))
    return "<" in exposed or "](" in exposed


def _cell_text(cell: str, block: Block, inline: InlineFn) -> str:
    span = block.meta.get("span")

    def unescape(match) -> str:
        value = span(match.group(0)) if span else None
        return "|" if value == "\\|" else match.group(0)

    text = inline(TOKEN_RE.sub(unescape, cell)).strip() if cell else ""
    return text or "blank"


def tables(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    if opts.table_style == "unchanged":
        return None
    header = split_row(block.lines[0])
    rows = [split_row(line) for line in block.lines[2:]]
    too_big = (len(rows) > MAX_ROWS or len(header) > MAX_COLUMNS
               or any(len(_original(cell, block)) > MAX_CELL for row in [header, *rows] for cell in row))
    malformed = (len(split_row(block.lines[1])) != len(header) or any(len(row) > len(header) for row in rows)
                 or any(_unsafe_cell(cell, block) for row in [header, *rows] for cell in row))
    if not opts.latin or too_big or malformed:
        return list(block.lines)  # pass through byte-identical
    names = [_cell_text(cell, block, inline) if cell else f"Column {i + 1}" for i, cell in enumerate(header)]
    columns = ", ".join(names)
    out = []
    if opts.verbosity == "brief":
        out.append(f"Table, {_plural(len(rows), 'row')}: {columns}.")
    else:
        out.append(f"Table, {_plural(len(rows), 'row')}, {_plural(len(names), 'column')}: {columns}.")
    for number, row in enumerate(rows, 1):
        if opts.verbosity == "full" and number % 10 == 0:
            out.append(f"Columns: {columns}.")
        cells = [_cell_text(cell, block, inline) for cell in row] + ["blank"] * (len(names) - len(row))
        if opts.verbosity == "brief":
            parts = cells
        else:
            parts = [f"{name} {value}" for name, value in zip(names, cells)]
        out.append(_sentence(f"Row {number}: " + ", ".join(parts)))
    if opts.verbosity != "brief":
        out.append("End of table.")
    # Rebuild protection from restored prose, not the original cell-local tokens. Math in
    # separate destinations may now pair before destination protection, while newly emitted
    # bare URLs must be protected before checking inline rules again.
    restored = [_original(line, block) for line in out]
    stash = Stash()
    protected = protect_code_spans(restored, stash, lambda line: False)
    next_opts = replace(opts, span=stash.value_of)
    checked = []
    active = inline_rules()
    for line in protected:
        text = protect_inline(line, stash)
        for rule in active:
            text = rule(text, next_opts)
        checked.extend(stash.restore(text))
    if checked != restored:
        return list(block.lines)
    # A table interrupts paragraphs; its spoken replacement does not. Keep the original
    # block boundary so neighbouring unmatched delimiters cannot capture restored spans.
    if block.meta.get("prev") and block.meta["prev"].strip():
        out.insert(0, "")
    if block.meta.get("next") and block.meta["next"].strip():
        out.append("")
    return out


register_block_rule("table", tables)
