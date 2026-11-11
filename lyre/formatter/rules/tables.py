"""R6: tables read as sentences (both profiles).

``Table, 2 rows, 3 columns: Name, Price, Stock.`` then one ``Row N:`` sentence per row that names
each column, then ``End of table.`` Every cell is kept; empty cells say ``blank``. Malformed or
oversized tables, and tables in mostly non-Latin replies, pass through byte-identical.
"""

from __future__ import annotations

from ..model import Block, Options
from ..spans import TOKEN_RE
from . import InlineFn, register_block_rule

MAX_ROWS = 50
MAX_COLUMNS = 10
MAX_CELL = 500
_END_PUNCT = (".", "!", "?")


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
               or any(len(cell) > MAX_CELL for row in [header, *rows] for cell in row))
    if not opts.latin or too_big or any(len(row) > len(header) for row in rows):
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
    return out


register_block_rule("table", tables)
