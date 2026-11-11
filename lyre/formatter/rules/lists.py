"""R5: lists (both profiles).

Items are numbered in words (``1, Build``) with a count line before each list; nesting is spoken
(``sub-item 2``, ``level 3 item 1``) and every nested line is indented exactly two spaces, so
the output never reads as indented code. Task boxes become ``(done)`` and ``(not done)``.
Mostly non-Latin replies keep the numbering but get no English words.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import Block, Options
from ..spans import LIST_ITEM_RE, indent_width, is_block_token_line
from . import InlineFn, register_block_rule
from .code import already_labelled, labelled


@dataclass
class _Item:
    number: str
    text: str
    extras: list = field(default_factory=list)  # ("line", text) | ("blank", "") | ("list", _List)


@dataclass
class _List:
    level: int
    indent: int
    ordered: bool
    items: list[_Item] = field(default_factory=list)


def _parse(lines: list[str]) -> _List | None:
    first = LIST_ITEM_RE.match(lines[0])
    if not first:
        return None
    root = _List(1, indent_width(first.group(1)), first.group(2)[0].isdigit())
    stack = [root]
    for line in lines:
        m = LIST_ITEM_RE.match(line)
        if m:
            indent, marker = indent_width(m.group(1)), m.group(2)
            while len(stack) > 1 and indent < stack[-1].indent:
                stack.pop()
            if indent > stack[-1].indent and stack[-1].items:
                sub = _List(stack[-1].level + 1, indent, marker[0].isdigit())
                stack[-1].items[-1].extras.append(("list", sub))
                stack.append(sub)
            target = stack[-1]
            number = marker[:-1] if marker[0].isdigit() else str(len(target.items) + 1)
            target.items.append(_Item(number, line[m.end():]))
        elif not stack[-1].items:
            return None
        elif line.strip():
            stack[-1].items[-1].extras.append(("line", line.strip()))
        else:
            stack[-1].items[-1].extras.append(("blank", ""))
    return root


def _task(text: str, opts: Options) -> str:
    if not opts.latin or len(text) < 3 or text[0] != "[" or text[2] != "]" or text[1] not in " xX":
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
            out.extend(pad + line if line else line for line in labelled(raw, opts) or [raw])
        else:
            text = inline(_task(raw, opts)).strip() or raw
            out.append(pad + _label(lst, item.number, opts) + text)
        for index, (kind, value) in enumerate(item.extras):
            if kind == "list":
                _emit(value, opts, inline, out)
            elif kind == "blank":
                out.append("")
            elif is_block_token_line(value):
                # Protected code, restored byte for byte later; labelled here because the list
                # rule owns it (a second pass sees it outside the list and must find the labels).
                lines = None if _labelled_nearby(item.extras, index) else labelled(value, opts)
                out.extend(pad + line if line else line for line in lines or [value])
            else:
                out.append(pad + (inline(value).strip() or value))


def _labelled_nearby(extras: list, index: int) -> bool:
    texts = [value for kind, value in extras if kind == "line"]
    lines = [value for kind, value in extras[:index] if kind == "line"]
    after = [value for kind, value in extras[index + 1:] if kind == "line"]
    return bool(texts) and already_labelled(lines[-1] if lines else None, after[0] if after else None)


def lists(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    root = _parse(block.lines)
    if root is None:
        return None
    out: list[str] = []
    _emit(root, opts, inline, out)
    while out and not out[-1].strip():
        out.pop()
    if opts.verbosity == "full" and opts.latin:
        out.append("End of list.")
    return out


register_block_rule("list", lists)
