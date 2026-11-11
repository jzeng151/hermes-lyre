"""R5: lists (both profiles).

Items are numbered in words (``1, Build``) with a count line before each list; nesting is spoken
(``sub-item 2``, ``level 3 item 1``) and every nested line is indented exactly two spaces, so
the output never reads as indented code. Task boxes become ``(done)`` and ``(not done)``.
Mostly non-Latin replies keep the numbering but get no English words.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import Block, Options
from ..blocks import syntax_categories
from ..spans import LIST_ITEM_RE, indent_width, is_block_token_line
from . import InlineFn, register_block_rule


@dataclass
class _Item:
    number: str
    text: str
    column: int  # where the item's content starts; continuation lines indented less leave it
    extras: list = field(default_factory=list)  # ("line", text) | ("blank", "") | ("list", _List)


@dataclass
class _List:
    level: int
    indent: int
    kind: str  # the bullet character or the ordered delimiter; a change starts a new list
    items: list[_Item] = field(default_factory=list)


def _kind(marker: str) -> str:
    return marker[-1] if marker[0].isdigit() else marker


def _new_list(stack: list[_List], roots: list[_List], level: int, indent: int, kind: str) -> _List:
    """Open a list at *level*: a sibling after the list it replaces, or a child of the open item."""
    lst = _List(level, indent, kind)
    if level == 1:
        roots.append(lst)
    else:
        stack[-1].items[-1].extras.append(("list", lst))
    stack.append(lst)
    return lst


def _parse(lines: list[str]) -> list[_List] | None:
    """The top-level lists in *lines*, or None when the block is not something this rule can speak.

    Continuation lines that start with block syntax (a heading, quote, rule or table inside an
    item) are not spoken here; the list is then left to the default inline handling.
    """
    if not LIST_ITEM_RE.match(lines[0]):
        return None
    roots: list[_List] = []
    stack: list[_List] = []
    prev_blank = False
    for line in lines:
        m = LIST_ITEM_RE.match(line)
        if m:
            indent, kind = indent_width(m.group(1)), _kind(m.group(2))
            while stack and indent < stack[-1].indent:
                stack.pop()
            if stack and indent == stack[-1].indent and kind != stack[-1].kind:
                stack.pop()  # same level, new marker type: a separate list
                _new_list(stack, roots, len(stack) + 1, indent, kind)
            elif not stack or (stack[-1].items and indent >= stack[-1].items[-1].column):
                # A marker nests only when it reaches the content column of the item above;
                # a smaller indent (`` - second`` under ``- first``) is a sibling.
                _new_list(stack, roots, len(stack) + 1, indent, kind)
            target = stack[-1]
            marker = m.group(2)
            number = marker[:-1] if marker[0].isdigit() else str(len(target.items) + 1)
            # Columns, not characters: a tab after the marker reaches the next tab stop (4).
            column = len(line[:m.end()].expandtabs(4)) if line[m.end():].strip() else indent + len(marker) + 1
            target.items.append(_Item(number, line[m.end():], column))
        elif not line.strip():
            prev_blank = True
            stack[-1].items[-1].extras.append(("blank", ""))
        else:
            if syntax_categories(line.strip(), None) - {"list"}:
                return None
            # After a blank line, return to the item that owns this paragraph (it may sit above a
            # nested list); directly after an item the line is a lazy continuation of it.
            while prev_blank and len(stack) > 1 and indent_width(line) < stack[-1].items[-1].column:
                stack.pop()
            stack[-1].items[-1].extras.append(("line", line.strip()))
        if line.strip():
            prev_blank = False
    return roots


def _task(text: str, opts: Options) -> str:
    if (not opts.latin or len(text) < 3 or text[0] != "[" or text[2] != "]" or text[1] not in " xX"
            or text[3:4] not in ("", " ", "\t")):
        return text
    rest = text[3:].lstrip()
    return ("(not done) " if text[1] == " " else "(done) ") + rest


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _count_line(lst: _List, opts: Options) -> str | None:
    if opts.verbosity == "brief" or not opts.latin:
        return None
    n = len(lst.items)
    noun = "item" if lst.level == 1 else "sub-item" if lst.level == 2 else f"level {lst.level} item"
    if opts.verbosity == "full":
        name = "List" if lst.level == 1 else "Sub-list" if lst.level == 2 else f"Level {lst.level} list"
        return f"{name}, {_plural(n, 'item')}."
    return f"{_plural(n, noun)}."


def _label(lst: _List, number: str, opts: Options) -> str:
    if lst.level == 1 or not opts.latin:
        return f"{number}, "
    if lst.level == 2:
        return f"sub-item {number}, "
    return f"level {lst.level} item {number}, "


def _emit(lst: _List, opts: Options, inline: InlineFn, out: list[str]) -> None:
    pad = "" if lst.level == 1 else "  "
    count = _count_line(lst, opts)
    if count:
        out.append(pad + count)
    for item in lst.items:
        raw = item.text.strip()
        if is_block_token_line(raw):
            # The item is a code block: number on its own line, code below it, so the fence
            # starts a line and stays protected on the next pass.
            out.append(pad + _label(lst, item.number, opts).rstrip())
            out.append(pad + raw)
        else:
            # An item the inline rules emptied (only decoration) keeps its number, nothing more.
            text = inline(_task(raw, opts)).strip()
            out.append((pad + _label(lst, item.number, opts) + text).rstrip())
        for kind, value in item.extras:
            if kind == "list":
                _emit(value, opts, inline, out)
            elif kind == "blank":
                out.append("")
            elif is_block_token_line(value):
                out.append(pad + value)  # protected code: restored byte for byte later
            else:
                text = inline(value).strip()
                if syntax_categories(text, None) - syntax_categories(value, None):
                    text = value  # the rules exposed block syntax (``🎉 - hidden``): keep the line
                if text:
                    out.append(pad + text)


def _unclosed_fence(lst: _List, opts: Options) -> bool:
    """True when an item's code is a fence with no closing line inside the item.

    Moving such a fence to its own output line would let it swallow everything after the list
    on the next pass, so the list is left as written.
    """
    for item in lst.items:
        raw = item.text.strip()
        value = opts.span(raw) if opts.span and is_block_token_line(raw) else None
        if value is not None and raw[1] == "f":
            lines = value.split("\n")
            fence = lines[0].lstrip()[:3]
            last = lines[-1].strip()
            if len(lines) < 2 or not last.startswith(fence) or last != last[0] * len(last):
                return True
        if any(kind == "list" and _unclosed_fence(value, opts) for kind, value in item.extras):
            return True
    return False


def lists(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    roots = _parse(block.lines)
    if roots is None or any(_unclosed_fence(root, opts) for root in roots):
        return None
    out: list[str] = []
    for root in roots:
        part: list[str] = []
        _emit(root, opts, inline, part)
        trailing = 0
        while part and not part[-1].strip():
            part.pop()
            trailing += 1
        if opts.verbosity == "full" and opts.latin:
            part.append("End of list.")
        out.extend(part + [""] * trailing)
    while out and not out[-1].strip():
        out.pop()
    return out


register_block_rule("list", lists)
