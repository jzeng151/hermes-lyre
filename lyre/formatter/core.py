"""The speech-formatter pipeline (spec: Processing model).

``format_for_speech`` never raises on reply content: any failure returns the input unchanged.
Rules live in ``lyre.formatter.rules``; with none registered the output equals the input.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace
from typing import cast

from . import rules
from .blocks import ATX_RE, QUOTE_RE, segment, starts_block, syntax_categories
from .model import (EMOJI_POLICIES, PROFILES, TABLE_STYLES, VERBOSITIES, Block, EmojiPolicy, Options, Profile,
                    TableStyle, Verbosity)
from .spans import (CLOSE, OPEN, TOKEN_RE, Stash, indent_width, is_block_token_line, protect_blocks, protect_cells,
                    protect_code_spans, protect_inline)

_ASCII_LETTER_PROBE = re.compile("[A-Za-z]")

MAX_BYTES = 200_000
MAX_QUOTE_DEPTH = 10
_REMOVED = object()  # marks where a block was removed, for blank-line normalization


class _TooDeep(Exception):
    """A quote nested past MAX_QUOTE_DEPTH; the outermost quote holding it stays unchanged."""


def format_for_speech(
    text: str,
    *,
    profile: Profile,
    verbosity: Verbosity = "normal",
    emoji_policy: EmojiPolicy = "words",
    table_style: TableStyle = "sentences",
    on_error: Callable[[Exception], None] | None = None,
) -> str:
    """Return *text* rewritten for a screen reader.

    Returns *text* itself when it is empty, over 200,000 UTF-8 bytes, contains Lyre's private
    placeholder characters, mixes line endings, fails anywhere in the pipeline, or would become
    empty. Raises ValueError only for an unknown option value, which is a caller bug, never a
    property of the reply. *on_error*, when given, receives the exception from a failed pipeline
    run (called inside the ``except`` block, so a logger can record the traceback); the formatter
    itself does no I/O and still returns *text*.
    """
    opts = _options(profile, verbosity, emoji_policy, table_style)
    if not isinstance(text, str) or not text.strip() or OPEN in text or CLOSE in text:
        return text
    if len(text.encode("utf-8", "surrogatepass")) > MAX_BYTES:
        return text
    crlf = "\r\n" in text
    bare = text.replace("\r\n", "")
    if "\r" in bare or (crlf and "\n" in bare):
        return text  # mixed or old-Mac line endings: leave alone rather than guess
    work = text.replace("\r\n", "\n") if crlf else text
    try:
        out = _process(work, opts, depth=0)
    except Exception as exc:  # health: allow BLE001 -- contract: any failure returns the reply unchanged
        if on_error is not None:
            on_error(exc)  # the caller (the hook) logs it
        return text
    if out == work or not out.strip():
        return text
    return out.replace("\n", "\r\n") if crlf else out


def _options(profile: str, verbosity: str, emoji_policy: str, table_style: str) -> Options:
    for name, value, allowed in (("profile", profile, PROFILES), ("verbosity", verbosity, VERBOSITIES),
                                 ("emoji_policy", emoji_policy, EMOJI_POLICIES),
                                 ("table_style", table_style, TABLE_STYLES)):
        if value not in allowed:
            raise ValueError(f"{name} must be one of {', '.join(allowed)}; got {value!r}")
    return Options(profile=cast(Profile, profile), verbosity=cast(Verbosity, verbosity),
                   emoji_policy=cast(EmojiPolicy, emoji_policy), table_style=cast(TableStyle, table_style))


def _letter_counts(lines: list[str]) -> tuple[int, int]:
    latin = total = 0
    for line in lines:
        text = TOKEN_RE.sub("", line)
        if text.isascii():
            count = len(_ASCII_LETTER_PROBE.findall(text))
            latin += count
            total += count
            continue
        for i, ch in enumerate(text):
            # A letter shown as emoji (information source with U+FE0F) is decoration, not script.
            if ch.isalpha() and text[i + 1:i + 2] != "\uFE0F":
                total += 1
                code = ord(ch)
                if code < 0x250 or 0x1E00 <= code <= 0x1EFF or 0x2C60 <= code <= 0x2C7F or 0xA720 <= code <= 0xA7FF:
                    latin += 1
    return latin, total


def is_latin(lines: list[str]) -> bool:
    """True unless fewer than half of the letters are Latin script (spec: Script detection).

    *lines* must already have their protected spans replaced by tokens.
    """
    latin, total = _letter_counts(lines)
    return total == 0 or latin * 2 >= total


def _protect(text: str, stash: Stash) -> list[str]:
    """Step 2 for one container level. Quote lines are protected by their own container pass."""
    lines = protect_blocks(text.split("\n"), stash)
    # Lists do not recursively render their nested quotes. Preserve those lines rather than
    # exposing their code (and any unsupported nested structure) to the list's inline rules.
    skip = lambda line: bool(is_block_token_line(line) or QUOTE_RE.match(line))  # noqa: E731
    out = []
    for block in segment(lines):
        if block.kind == "list":
            block.lines = [stash.put("t", line) if QUOTE_RE.match(line) else line for line in block.lines]
        if block.kind == "blockquote" and any(not QUOTE_RE.match(line) for line in block.lines):
            # Lazy continuations lack marker prefixes. Keep this unsupported container whole,
            # rather than exposing a cross-line code span or inventing quote markers.
            out.append(stash.put("t", "\n".join(block.lines)))
        elif block.kind == "table":
            out.extend(protect_cells(line, stash) for line in block.lines)
        else:
            protected = protect_code_spans(block.lines, stash, skip, starts_block, lambda line: bool(ATX_RE.match(line)))
            out.extend(line if skip(line) else protect_inline(line, stash) for line in protected)
    return out


def _reply_letter_counts(text: str, depth: int = 0) -> tuple[int, int]:
    """Letters outside protected spans, quote contents included (each quote protected as a container)."""
    return _protected_letter_counts(_protect(text, Stash()), depth)


def _protected_letter_counts(lines: list[str], depth: int = 0) -> tuple[int, int]:
    """Count already-protected lines, descending into quote containers only."""
    latin, total = _letter_counts([line for line in lines if not QUOTE_RE.match(line)])
    if depth < MAX_QUOTE_DEPTH:
        # Each contiguous quote is its own container, as in _render_quote: an unclosed fence in
        # one quote must not swallow the letters of the next.
        runs: list[list[str]] = [[]]
        for line in lines:
            if QUOTE_RE.match(line):
                runs[-1].append(_strip_quote_marker(line)[1])
            elif runs[-1]:
                runs.append([])
        for run in runs:
            if run:
                q_latin, q_total = _reply_letter_counts("\n".join(run), depth + 1)
                latin, total = latin + q_latin, total + q_total
    return latin, total


def _strip_quote_marker(line: str) -> tuple[str, str]:
    """Split one quote line into its marker prefix and its contents."""
    body = line.lstrip(" ")[1:]
    if body.startswith(" "):
        body = body[1:]
    return line[: len(line) - len(body)], body


def _process(text: str, opts: Options, depth: int) -> str:
    stash = Stash()
    lines = _protect(text, stash)
    if depth == 0:
        latin, total = _protected_letter_counts(lines)
        opts = replace(opts, latin=total == 0 or latin * 2 >= total)
    opts = replace(opts, span=stash.value_of)
    entries: list = []
    blocks = segment(lines)
    for i, block in enumerate(blocks):
        block.meta["prev"] = blocks[i - 1].lines[-1] if i else None
        block.meta["next"] = blocks[i + 1].lines[0] if i + 1 < len(blocks) else None
        block.meta["span"] = stash.value_of
    _nearest_text(blocks)
    prev_out, prev_changed = None, False  # last rendered line of the previous block
    for block in blocks:
        out = _render(block, opts, depth)
        if out is not None and not any(line.strip() for line in out) and _before_indented_code(block):
            # The block may end a list above; removing it could turn the code into list text.
            # Keep its paragraph boundary too: an inserted code label must not join this
            # retained decoration and let the next pass remove it from a larger paragraph.
            following = block.meta.get("next")
            out = [*block.lines, ""] if following and is_block_token_line(following) else None
        first = block.lines[0] if out is None else (out[0] if out else None)
        changed = out is not None
        if first is not None and (changed or prev_changed) and _exposed_at_boundary(first, prev_out):
            entries.append(("", True))  # keep the blocks apart (a new Setext underline or table)
        if block.kind == "blank":
            prev_out, prev_changed = None, False
        elif out != []:
            prev_out, prev_changed = (block.lines if out is None else out)[-1], changed
        else:
            prev_changed = True  # a removed block gives the surviving blocks a new neighbour
        if out is None:
            entries.extend((line, False) for line in block.lines)
        elif not out:
            entries.append(_REMOVED)
        else:
            # Only lines a rule actually changed lose trailing spaces (a Markdown hard break
            # on an untouched line stays).
            # A quote's contents were normalized by their own pass and may hold restored code.
            originals = set(block.lines)
            trim = block.kind != "blockquote"
            entries.extend((line.rstrip(" \t") if trim and line not in originals else line, line not in originals)
                           for line in out)
    final: list[str] = []
    for line in _normalize(entries):
        final.extend(stash.restore(line))
    return "\n".join(final)


def _before_indented_code(block: Block) -> bool:
    following = block.meta.get("next_non_math_text")
    if following is not None and rules.is_code_label(following):
        return True  # after the first pass the code has its label above it
    return following is not None and is_block_token_line(following) and following.strip()[1] in ("c", "f")


def _nearest_text(blocks: list[Block]) -> None:
    """Record each block's nearest non-blank line before and after it (``prev_text``, ``next_text``).

    Rules use them to recognize their own earlier output, such as code labels around a block.
    """
    last = None
    for block in blocks:
        block.meta["prev_text"] = last
        if block.kind != "blank":
            last = block.lines[-1]
    following = non_math = None
    for block in reversed(blocks):
        block.meta["next_text"] = following
        block.meta["next_non_math_text"] = non_math
        if block.kind != "blank":
            following = block.lines[0]
            # Display math preserves list context in protect_blocks; look through it when
            # deciding whether removing a terminator would expose later protected code.
            if block.kind != "math":
                non_math = following


def _exposed_at_boundary(first: str, prev_out: str | None) -> bool:
    """True when a block's first line gains block syntax from the rendered line above it.

    Each block is guarded on its own (step 6); this catches what only the neighbour shows, such
    as ``===`` becoming the underline of a heading rewritten into a paragraph line. In the input
    a block boundary never carries such syntax (the segmenter would have joined the lines), so
    any gain is new. Only checked where one of the two blocks changed.
    """
    if prev_out is None or not prev_out.strip():
        return False
    return bool(syntax_categories(first, prev_out) - syntax_categories(first, None))


def _inline_fn(opts: Options):
    active = rules.inline_rules()

    def inline(text: str) -> str:
        for rule in active:
            text = rule(text, opts)
            if "\n" in text:
                raise ValueError("an inline rule produced a newline")
        return text

    return inline


def _render(block: Block, opts: Options, depth: int) -> list[str] | None:
    """Replacement lines for *block*, ``[]`` to remove it, or None when nothing changed."""
    if block.kind == "blockquote":
        # The contents already went through this pipeline (guard included); dropping the
        # markers only reveals structure that was there, so the guard does not apply.
        try:
            out = _render_quote(block, opts, depth)
        except _TooDeep:
            if depth:
                raise
            return None
        return None if out is None or out == block.lines else out
    inline = _inline_fn(opts)
    rule = rules.block_rule(block.kind)
    out = rule(block, opts, inline) if rule else None
    per_line = out is None
    if per_line and block.kind in ("paragraph", "heading", "list", "table"):
        out = _inline_lines(block.lines, inline)
    if out is None or out == block.lines:
        return None
    return _guard(block.lines, out, per_line)


def _inline_lines(lines: list[str], inline) -> list[str]:
    out = []
    for line in lines:
        new = inline(line)
        if new.strip() or not line.strip():
            out.append(new)
    if out and lines and out[0] is not lines[0] and indent_width(out[0]) >= 4 and indent_width(lines[0]) < 4:
        # A removed first line left an indented continuation leading the block, which the next
        # pass would read as code. Indentation of a continuation line carries no meaning.
        out[0] = out[0].lstrip(" \t")
    return out


def _render_quote(block: Block, opts: Options, depth: int) -> list[str] | None:
    if depth >= MAX_QUOTE_DEPTH:
        raise _TooDeep
    prefixes, inner = [], []
    for line in block.lines:
        prefix, body = _strip_quote_marker(line)
        prefixes.append(prefix)
        inner.append(body)
    inner_out = _process("\n".join(inner), opts, depth + 1).split("\n")
    block.meta.update(inner=inner, inner_out=inner_out, prefixes=prefixes)
    rule = rules.block_rule("blockquote")
    out = rule(block, opts, _inline_fn(opts)) if rule else None
    if out is not None:
        return out
    if inner_out == inner:
        return None
    marker = prefixes[0].rstrip(" ") + " "
    return [(marker + line) if line.strip() else marker.rstrip(" ") for line in inner_out]


def _guard(before: list[str], after: list[str], per_line: bool) -> list[str]:
    """Step 6: undo output that starts with block syntax its input did not start with.

    Inline rules map lines one to one, so a single exposed line is restored on its own. A block
    rule's output is all or nothing: one exposed line restores the whole block.
    """
    if per_line and len(before) == len(after):
        guarded = []
        for i, (old, new) in enumerate(zip(before, after)):
            if new == old and (i == 0 or before[i - 1] == after[i - 1]):
                guarded.append(old)
                continue
            exposed = syntax_categories(new, after[i - 1] if i else None)
            if exposed:
                exposed -= syntax_categories(old, before[i - 1] if i else None)
            guarded.append(old if exposed else new)
        return guarded
    categories = [syntax_categories(line, after[i - 1] if i else None) for i, line in enumerate(after)]
    if not any(categories):
        return after
    had: set[str] = set()
    for i, line in enumerate(before):
        had |= syntax_categories(line, before[i - 1] if i else None)
    for category in categories:
        if category - had:
            return before
    return after


def _normalize(entries: list) -> list[str]:
    """Step 7: collapse blank runs that a removal created; leave every other run alone."""
    out: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        if entry is _REMOVED or not entry[0].strip():
            j, touched = i, False
            while j < len(entries) and (entries[j] is _REMOVED or not entries[j][0].strip()):
                touched = touched or entries[j] is _REMOVED
                j += 1
            run = [e[0] for e in entries[i:j] if e is not _REMOVED]
            if touched:
                # A removal never joins its neighbours: between two blocks one blank line stays.
                at_edge = i == 0 or j == len(entries)
                run = [] if at_edge else [""]
            out.extend(run)
            i = j
            continue
        out.append(entry[0])
        i += 1
    return out
