"""Block pass (processing step 3) and the block-syntax categories the guard (step 6) checks.

Each block kind is recognized with anchored patterns on one line at a time; the pass walks the
lines once. ``meta`` keys: heading ``level`` and ``setext``; code and math ``token_kind``.
"""

from __future__ import annotations

import re

from .model import Block
from .spans import FENCE_OPEN_RE, LIST_ITEM_RE, block_token_kind, indent_width, list_content_column

ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]|$)")
SETEXT_RE = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")
QUOTE_RE = re.compile(r"^ {0,3}>")
FENCE_RE = re.compile(r"^[ \t]*(?:`{3,}|~{3,})")
_SEP_CELL_RE = re.compile(r":?-+:?")


def is_table_separator(line: str) -> bool:
    """``|---|:--:|`` and ``---|---``: needs a pipe; checked cell by cell in linear time."""
    body = line.strip()
    if "|" not in body:
        return False
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") else body
    return all(_SEP_CELL_RE.fullmatch(cell.strip()) for cell in body.split("|"))


def is_thematic_break(line: str) -> bool:
    if indent_width(line) > 3:
        return False
    body = line.replace(" ", "").replace("\t", "")
    return len(body) >= 3 and body[0] in "-*_" and body == body[0] * len(body)


def _is_table_start(lines: list[str], i: int) -> bool:
    return "|" in lines[i] and i + 1 < len(lines) and is_table_separator(lines[i + 1])


def starts_block(line: str) -> bool:
    """True when *line* interrupts a paragraph; inline content never continues across it."""
    return bool(block_token_kind(line) or QUOTE_RE.match(line) or ATX_RE.match(line)
                or is_thematic_break(line) or LIST_ITEM_RE.match(line))


def syntax_categories(line: str, prev: str | None) -> set[str]:
    """Block syntax *line* starts with; *prev* is the line above (setext underlines need it)."""
    found = set()
    if LIST_ITEM_RE.match(line):
        found.add("list")
    if ATX_RE.match(line):
        found.add("atx")
    if QUOTE_RE.match(line):
        found.add("quote")
    if line.lstrip().startswith("|") or (prev is not None and "|" in prev and is_table_separator(line)):
        found.add("table")
    if is_thematic_break(line):
        found.add("rule")
    if FENCE_RE.match(line):
        found.add("fence")
    if line.lstrip().startswith("$$"):
        found.add("math")  # a newly exposed opener can change which later lines are protected
    if SETEXT_RE.match(line) and prev is not None and prev.strip():
        found.add("setext")
    return found


def _take_while(lines: list[str], i: int, keep) -> int:
    j = i + 1
    while j < len(lines) and keep(lines[j]):
        j += 1
    return j


def _item_column(line: str, default: int) -> int:
    column = list_content_column(line)
    return column if column is not None and not is_thematic_break(line) else default


def _list_end(lines: list[str], i: int) -> int:
    j, column = i + 1, _item_column(lines[i], 2)
    while j < len(lines):
        line = lines[j]
        if not line.strip():
            k = j
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines) and (LIST_ITEM_RE.match(lines[k]) or indent_width(lines[k]) >= 2):
                j = k
                continue
            break
        if is_thematic_break(line) and indent_width(line) < column:
            break  # ``* * *`` looks like an item but is a break; left of the item's text it ends the list
        column = _item_column(line, column)
        if not LIST_ITEM_RE.match(line) and indent_width(line) < column and starts_block(line):
            break  # a heading or quote left of the item's text is outside the list
        j += 1
    return j


def _quote_end(lines: list[str], i: int) -> int:
    """Include lazy paragraph continuations, but never lazily continue a closed block."""
    j, paragraph, fence = i, False, None
    while j < len(lines):
        line = lines[j]
        quote = QUOTE_RE.match(line)
        if quote:
            body = line[quote.end():].removeprefix(" ")
            while nested := QUOTE_RE.match(body):
                body = body[nested.end():].removeprefix(" ")
            if fence is not None:
                stripped = body.strip()
                if len(stripped) >= len(fence) and stripped == fence[0] * len(stripped):
                    fence = None
                paragraph = False
            else:
                opening = FENCE_OPEN_RE.match(body)
                if opening and indent_width(body) < 4:
                    fence = opening.group(2)
                    paragraph = False
                else:
                    paragraph = bool(body.strip()) and not (
                        starts_block(body) or SETEXT_RE.match(body)
                        or (not paragraph and indent_width(body) >= 4))
        elif not paragraph or not line.strip() or starts_block(line) or SETEXT_RE.match(line) or _is_table_start(lines, j):
            break
        j += 1
    return j


def _paragraph(lines: list[str], i: int) -> tuple[Block, int]:
    j = i + 1
    while j < len(lines) and lines[j].strip():
        if SETEXT_RE.match(lines[j]):
            level = 1 if lines[j].strip()[0] == "=" else 2
            return Block("heading", lines[i:j + 1], {"level": level, "setext": True}), j + 1
        if starts_block(lines[j]) or _is_table_start(lines, j):
            break  # a table may interrupt a paragraph (GFM), as in "Results:" over a table
        j += 1
    return Block("paragraph", lines[i:j]), j


def _one_block(lines: list[str], i: int) -> tuple[Block, int]:
    line = lines[i]
    token_kind = block_token_kind(line)
    if not line.strip():
        return Block("blank", [line]), i + 1
    if token_kind:
        return Block(token_kind, [line], {"token_kind": token_kind}), i + 1
    if QUOTE_RE.match(line):
        j = _quote_end(lines, i)
        return Block("blockquote", lines[i:j]), j
    atx = ATX_RE.match(line)
    if atx:
        return Block("heading", [line], {"level": len(atx.group(1)), "setext": False}), i + 1
    if is_thematic_break(line):
        return Block("rule", [line]), i + 1
    if _is_table_start(lines, i):
        # GFM: rows run to a blank line or the start of another block (even one holding a
        # pipe); a short row may have no pipe.
        j = _take_while(lines, i, lambda s: bool(s.strip()) and not starts_block(s))
        return Block("table", lines[i:j]), j
    if LIST_ITEM_RE.match(line):
        j = _list_end(lines, i)
        return Block("list", lines[i:j]), j
    return _paragraph(lines, i)


def segment(lines: list[str]) -> list[Block]:
    """Group protected lines into blocks in one pass."""
    blocks, i = [], 0
    while i < len(lines):
        block, i = _one_block(lines, i)
        blocks.append(block)
    return blocks
