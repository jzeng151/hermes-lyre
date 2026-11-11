"""R5: lists (both profiles).

Items are numbered in words (``1, Build``) with a count line before each list; nesting is spoken
(``sub-item 2``, ``level 3 item 1``) and every nested line is indented exactly two spaces, so
the output never reads as indented code. Task boxes become ``(done)`` and ``(not done)``.
Mostly non-Latin replies keep the numbering but get no English words.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from ..model import Block, Options
from ..blocks import is_thematic_break, syntax_categories
from ..spans import LIST_ITEM_RE, indent_width, is_block_token_line
from . import InlineFn, register_block_rule
from .code import LABEL_RE, already_labelled, labelled

# Match just the opener: destinations and titles may continue on subsequent lines.
_REF_DEF_START_RE = re.compile(r"^\[[^\]\n]+\]:")


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
    owner: int = 0  # the column a marker must reach to stay in this list (parent's content column)
    items: list[_Item] = field(default_factory=list)


def _kind(marker: str) -> str:
    return marker[-1] if marker[0].isdigit() else marker


def _new_list(stack: list[_List], roots: list[_List], level: int, indent: int, kind: str) -> _List:
    """Open a list at *level*: a sibling after the list it replaces, or a child of the open item."""
    # A top-level list belongs to the reply itself (column 0); its markers may sit 0 to 3 spaces in.
    lst = _List(level, indent, kind, 0 if level == 1 else stack[-1].items[-1].column)
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
    for i, line in enumerate(lines):
        # Paired and escaped backticks are already tokens. Any remaining backtick is unmatched
        # in its inline container; dropping item markers could pair it with another item's code.
        if "`" in line:
            return None
        m = LIST_ITEM_RE.match(line)
        content = line[m.end():] if m else line
        if _REF_DEF_START_RE.match(content.lstrip()):
            # Spoken numbering would turn a block definition into prose and break its links.
            return None
        if m and (is_thematic_break(line) or LIST_ITEM_RE.match(line[m.end():])):
            return None  # ``* * *`` is a break, not an item; ``- - a`` nests on the marker line
        if m:
            indent, kind = indent_width(m.group(1)), _kind(m.group(2))
            # A nested list ends only at a marker left of its parent's content column; a marker
            # less indented than its siblings but still inside the parent stays in the list.
            while stack and indent < stack[-1].owner:
                stack.pop()
            if not stack or (stack[-1].items and indent >= stack[-1].items[-1].column):
                # A marker nests only when it reaches the content column of the item above;
                # a smaller indent (`` - second`` under ``- first``) is a sibling.
                _new_list(stack, roots, len(stack) + 1, indent, kind)
            elif kind != stack[-1].kind:
                stack.pop()  # a sibling with a new marker type: a separate list at this level
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
            # Setext underlines are block syntax only with the preceding nonblank line.
            if syntax_categories(line.strip(), lines[i - 1] if i else None) - {"list"}:
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
            out.extend(pad + line if line else line for line in labelled(raw, opts) or [raw])
        elif LABEL_RE.match(raw):
            # A code label as the item's text: on its own line, so the next pass still sees the
            # label directly above the code it names.
            out.append(pad + _label(lst, item.number, opts).rstrip())
            out.append(pad + raw)
        else:
            # An item the inline rules emptied (only decoration) keeps its number, nothing more.
            text = inline(_task(raw, opts)).strip()
            out.append((pad + _label(lst, item.number, opts) + text).rstrip())
        labelled_at = _labelled_neighbours(item.extras, item.text.strip())
        for index, (kind, value) in enumerate(item.extras):
            if kind == "list":
                _emit(value, opts, inline, out)
            elif kind == "blank":
                out.append("")
            elif is_block_token_line(value):
                # Protected code, restored byte for byte later; labelled here because the list
                # rule owns it (a second pass sees it outside the list and must find the labels).
                lines = None if labelled_at[index] else labelled(value, opts)
                out.extend(pad + line if line else line for line in lines or [value])
            else:
                text = inline(value).strip()
                if syntax_categories(text, None) - syntax_categories(value, None):
                    text = value  # the rules exposed block syntax (``🎉 - hidden``): keep the line
                if text:
                    out.append(pad + text)


def _labelled_neighbours(extras: list, opening: str | None = None) -> list[bool]:
    """For each extra, whether the nearest text lines around it are a code label and its end.

    Two linear passes, so an item holding many code blocks stays linear.
    """
    before: list[str | None] = []
    last = opening or None  # the item's own text is the first line above its extras
    for kind, value in extras:
        before.append(last)
        if kind == "line":
            last = value
    after: list[str | None] = [None] * len(extras)
    following = None
    for index in range(len(extras) - 1, -1, -1):
        after[index] = following
        if extras[index][0] == "line":
            following = extras[index][1]
    return [already_labelled(b, a) for b, a in zip(before, after)]


def _unsafe_fence(token: str, opts: Options) -> bool:
    value = opts.span(token) if opts.span and is_block_token_line(token) else None
    if value is None or token.strip()[1] != "f":
        return False
    lines = value.split("\n")
    opener = lines[0].lstrip()
    fence = opener[:len(opener) - len(opener.lstrip(opener[:1]))]  # the whole run, ```` or ~~~~~
    last = lines[-1].strip()
    closed = len(lines) >= 2 and len(last) >= len(fence) and last == fence[0] * len(last)
    # Restoration discards the token's output padding, even in nested lists. A fence lifted
    # off an item marker therefore starts at column zero; its closer must still be valid there.
    return not closed or indent_width(lines[-1]) > indent_width(lines[0]) + 3


def _has_unsafe_fence(lst: _List, opts: Options) -> bool:
    """True when an item's fence cannot safely leave its list container.

    Fences on item and continuation lines count alike: a missing or over-indented closer
    could swallow later content without the container, so the list stays as written.
    """
    for item in lst.items:
        if _unsafe_fence(item.text.strip(), opts):
            return True
        for kind, value in item.extras:
            if kind == "list" and _has_unsafe_fence(value, opts):
                return True
            if kind == "line" and _unsafe_fence(value, opts):
                return True
    return False


def lists(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    roots = _parse(block.lines)
    if roots is None or any(_has_unsafe_fence(root, opts) for root in roots):
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
    # Trailing blanks may separate this list from protected indented code in the next block.
    # Keep them after the full-verbosity end label too, so the next pass still sees code.
    return out


register_block_rule("list", lists)
