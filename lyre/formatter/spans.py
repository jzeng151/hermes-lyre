"""Span protection (processing step 2): code, math, escapes, HTML, URLs and link targets are
swapped for placeholder tokens so no rule can change them, then restored at the end.

Tokens are ``OPEN + kind + index + CLOSE`` built from private-use characters. The core refuses
input that already contains either character, so a token can never collide with reply text.
Block tokens (``f`` fenced code, ``m`` display math, ``c`` indented code) replace whole lines;
inline tokens replace part of a line.
"""

from __future__ import annotations

import bisect
import re

OPEN, CLOSE = "\ue000", "\ue001"
TOKEN_RE = re.compile("\ue000([a-z])(\\d+)\ue001")
BLOCK_TOKEN_RE = re.compile("^[ \t]*(\ue000[fmc]\\d+\ue001)[ \t]*$")
BLOCK_KINDS = {"f": "code", "c": "code", "m": "math"}

FENCE_OPEN_RE = re.compile(r"^([ \t]*)(`{3,}|~{3,})(.*)$")
LIST_ITEM_RE = re.compile(r"^([ \t]*)([-*+]|\d{1,9}[.)])([ \t]+|$)")
ESCAPE_RE = re.compile(r"\\[!-/:-@\[-`{-~]")
HTML_TAG_RE = re.compile(r"""</?[A-Za-z][A-Za-z0-9-]*(?:\s(?:[^<>"'\n]|"[^"\n]*"|'[^'\n]*')*)?/?>""")
# The same tag with attributes on later lines; only matches that cross a line are stashed this way.
HTML_TAG_MULTILINE_RE = re.compile(r"""<[A-Za-z][A-Za-z0-9-]*\s(?:[^<>"']|"[^"]*"|'[^']*')*/?>""")
INLINE_MATH_RE = re.compile(r"\$\$[^$\n]+\$\$")
URL_RE = re.compile("(?:https?|ftp)://[^\\s<>\ue000\ue001]+")
URL_TRAILING = ".,;:!?'\"*_"


class Stash:
    """Holds the original text of every protected span, indexed by token."""

    def __init__(self) -> None:
        self.values: list[str] = []
        self.kinds: list[str] = []

    def put(self, kind: str, value: str) -> str:
        self.values.append(value)
        self.kinds.append(kind)
        return f"{OPEN}{kind}{len(self.values) - 1}{CLOSE}"

    def value_of(self, token: str) -> str | None:
        """Original text of one token, for rules that must read a protected span."""
        m = TOKEN_RE.fullmatch(token)
        return self.values[int(m.group(2))] if m else None

    def restore(self, line: str) -> list[str]:
        """Return the original line(s) for one output line."""
        whole = BLOCK_TOKEN_RE.match(line)
        if whole:
            return self._expand(whole.group(1)).split("\n")
        return self._expand(line).split("\n")

    def _expand(self, text: str) -> str:
        # Values never contain tokens, so one pass suffices; the loop guards against a rule
        # that copied a token into another span's surroundings.
        for _ in range(4):
            if OPEN not in text:
                break
            text = TOKEN_RE.sub(lambda m: self.values[int(m.group(2))], text)
        return text


def indent_width(line: str) -> int:
    width = 0
    for ch in line:
        if ch == " ":
            width += 1
        elif ch == "\t":
            width += 4 - width % 4
        else:
            break
    return width


def is_block_token_line(line: str) -> bool:
    return bool(BLOCK_TOKEN_RE.match(line))


def block_token_kind(line: str) -> str | None:
    m = BLOCK_TOKEN_RE.match(line)
    return BLOCK_KINDS[m.group(1)[1]] if m else None


def marker_gap(m: re.Match) -> int:
    """Columns of whitespace after a list marker, with tabs expanded to stops of 4."""
    line = m.string
    return len(line[:m.end(3)].expandtabs(4)) - len(line[:m.start(3)].expandtabs(4))


def _list_content_column(line: str) -> int | None:
    m = LIST_ITEM_RE.match(line)
    if not m:
        return None
    gap = marker_gap(m)
    # A gap over 4 columns means the item text is indented code; content starts after 1 space.
    return indent_width(m.group(1)) + len(m.group(2)) + (1 if gap == 0 or gap > 4 else gap)


def _fence_end(lines: list[str], start: int, fence: str) -> int:
    """Index of the closing fence line, or the last line when the fence never closes."""
    char, size = fence[0], len(fence)
    for j in range(start + 1, len(lines)):
        body = lines[j].strip()
        if len(body) >= size and body == char * len(body):
            return j
    return len(lines) - 1


def _math_end(lines: list[str], start: int) -> int | None:
    first = lines[start].strip()
    if "$$" in first[2:]:
        # Closed on its own line: a display block only when nothing follows the closing $$;
        # otherwise it is inline math in a paragraph, protected by the inline pass.
        return start if first.index("$$", 2) + 2 == len(first) else None
    for j in range(start + 1, len(lines)):
        if "$$" in lines[j]:
            return j
    return None


def _indented_end(lines: list[str], start: int, threshold: int) -> int:
    end = start
    for j in range(start + 1, len(lines)):
        if lines[j].strip() and indent_width(lines[j]) < threshold:
            break
        if lines[j].strip():
            end = j
    return end


def _stash_lines(out: list[str], lines: list[str], start: int, end: int, kind: str, stash: Stash) -> None:
    lead = lines[start][: len(lines[start]) - len(lines[start].lstrip(" \t"))]
    out.append(lead + stash.put(kind, "\n".join(lines[start:end + 1])))


def _code_threshold(line: str, prev_blank: bool, list_col: int | None) -> int | None:
    """Indentation that makes *line* start an indented code block, if it can start one."""
    if not prev_blank or not line.strip():
        return None
    threshold = 4 if list_col is None else list_col + 4
    return threshold if indent_width(line) >= threshold else None


_ENDS_LIST_RE = re.compile(r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|>|(?:[-*_][ \t]*){3,}$)")


def _track_list(line: str, prev_blank: bool, list_col: int | None) -> int | None:
    col = _list_content_column(line)
    if col is not None:
        return col
    if list_col is None or not line.strip() or indent_width(line) >= list_col:
        return list_col
    # Outdented text after a blank line, or a heading, quote or rule, ends the list; outdented
    # text right after an item is a lazy continuation and keeps it.
    return None if prev_blank or _ENDS_LIST_RE.match(line) else list_col


def _item_fence(line: str) -> tuple[int, re.Match] | None:
    """A fence opening right after a list marker (``- ```py``): (offset of the fence, match).

    Not when 5+ spaces follow the marker: that content is indented code, protected elsewhere.
    """
    item = LIST_ITEM_RE.match(line)
    if not item or marker_gap(item) > 4:
        return None
    fence = FENCE_OPEN_RE.match(line[item.end():])
    if not fence or (fence.group(2)[0] == "`" and "`" in fence.group(3)):
        return None
    return item.end(), fence


def _item_fence_end(lines: list[str], start: int, fence: str, column: int) -> int:
    """Closing line of a fence opened on an item line, searched only inside that item.

    Without a closing fence inside the item, the block ends with the item's last line, so an
    unclosed fence never swallows the items and prose after it.
    """
    char, size, last = fence[0], len(fence), start
    for j in range(start + 1, len(lines)):
        body = lines[j].strip()
        if body and indent_width(lines[j]) < column:
            break
        if len(body) >= size and body == char * len(body):
            return j
        if body:
            last = j
    return last


def protect_blocks(lines: list[str], stash: Stash) -> list[str]:
    """Replace fenced code, display math and indented code with one token line each.

    A fence opened on a list item line keeps the marker: the line becomes ``- <token>``.
    """
    out: list[str] = []
    i, prev_blank, list_col = 0, True, None
    while i < len(lines):
        line = lines[i]
        item_fence = None if _code_threshold(line, prev_blank, list_col) is not None else _item_fence(line)
        if item_fence:
            offset, fence = item_fence
            list_col = _list_content_column(line)
            end = _item_fence_end(lines, i, fence.group(2), list_col)
            out.append(line[:offset] + stash.put("f", "\n".join([line[offset:], *lines[i + 1:end + 1]])))
            i, prev_blank = end + 1, False
            continue
        fence = FENCE_OPEN_RE.match(line)
        if fence and not (fence.group(2)[0] == "`" and "`" in fence.group(3)):
            if list_col is not None and indent_width(line) >= list_col:
                end = _item_fence_end(lines, i, fence.group(2), list_col)  # bounded by its item
            else:
                end = _fence_end(lines, i, fence.group(2))
            _stash_lines(out, lines, i, end, "f", stash)
            i, prev_blank = end + 1, False
            continue
        if line.lstrip().startswith("$$"):
            end = _math_end(lines, i)
            if end is not None:
                _stash_lines(out, lines, i, end, "m", stash)
                i, prev_blank = end + 1, False
                continue
        item = LIST_ITEM_RE.match(line)
        if item and marker_gap(item) > 4 and line[item.end():].strip():
            # The item's content is indented code (marker, then 5+ spaces): keep the item as
            # code, with the code lines that continue it; Lyre does not speak this rare form.
            column = indent_width(item.group(1)) + len(item.group(2)) + 1
            end = _indented_end(lines, i, column + 4)
            _stash_lines(out, lines, i, end, "c", stash)
            i, prev_blank = end + 1, False
            continue
        threshold = _code_threshold(line, prev_blank, list_col)
        if threshold is not None:
            end = _indented_end(lines, i, threshold)
            _stash_lines(out, lines, i, end, "c", stash)
            i, prev_blank = end + 1, False
            continue
        list_col = _track_list(line, prev_blank, list_col)
        out.append(line)
        prev_blank = not line.strip()
        i += 1
    return out


def _escaped(line: str, index: int) -> bool:
    """True when an odd run of backslashes precedes *index* (an even run escapes itself)."""
    count = 0
    while index - count > 0 and line[index - count - 1] == "\\":
        count += 1
    return count % 2 == 1


def _protect_code_spans(line: str, stash: Stash) -> str:
    # A tag can hide an opener, but not a closer: tag-shaped text after a code opener
    # is literal code. Keep all runs so a closer inside that literal is still available.
    tags = [m.span() for m in HTML_TAG_MULTILINE_RE.finditer(line)] if "<" in line else []
    tag_ends = [end for _, end in tags]
    runs: list[tuple[int, int]] = []
    i = 0
    while True:
        j = line.find("`", i)
        if j < 0:
            break
        k = j
        while k < len(line) and line[k] == "`":
            k += 1
        runs.append((j, k - j))
        i = k
    if len(runs) < 2:
        return line
    by_len: dict[int, list[int]] = {}
    for idx, (_, size) in enumerate(runs):
        by_len.setdefault(size, []).append(idx)
    out, pos, idx = [], 0, 0
    while idx < len(runs):
        start, size = runs[idx]
        if start < pos or _escaped(line, start):
            idx += 1
            continue
        t = bisect.bisect_right(tag_ends, start)
        if t < len(tags) and pos <= tags[t][0] < start:
            idx += 1
            continue  # a real HTML tag started outside any preceding code span
        same = by_len[size]
        nxt = bisect.bisect_right(same, idx)
        if nxt == len(same):
            idx += 1
            continue
        close = runs[same[nxt]][0]
        out.append(line[pos:start])
        out.append(stash.put("i", line[start:close + size]))
        pos, idx = close + size, same[nxt] + 1
    out.append(line[pos:])
    return "".join(out)


MAX_UNMATCHED_TARGETS = 32
REF_DEF_NEXT_LINE_RE = re.compile(r"^( {0,3}\[[^\]\n]+\]:[ \t]*\n[ \t]*)(<[^>\n]*>|\S+)", re.M)


def _target_end(line: str, k: int) -> int | None:
    """Index just past the ``)`` that closes a link target starting at *k*, or None.

    An angle-bracket destination and a quoted title are units, so parentheses inside them do
    not count; a backslash escapes the next character.
    """
    while k < len(line) and line[k] in " \t\n":
        k += 1  # optional whitespace before the destination (kept in the stashed text)
    if line.startswith("<", k):
        close = line.find(">", k)
        if close != -1:
            k = close + 1
    depth = 1
    while k < len(line) and depth:
        ch = line[k]
        if ch in "\"'" and line[k - 1] in " \t":
            close = line.find(ch, k + 1)
            if close != -1:
                k = close + 1
                continue
        if ch == "\\":
            k += 2
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        k += 1
    return None if depth else k


def _protect_link_targets(line: str, stash: Stash, multiline_only: bool = False) -> str:
    """Stash each link target. With *multiline_only*, only targets that cross one or two line
    breaks (CommonMark allows one before the destination and one before the title)."""
    out, pos, unmatched = [], 0, 0
    while True:
        j = line.find("](", pos)
        if j < 0:
            break
        k = _target_end(line, j + 2)
        if k is None:
            unmatched += 1
            if unmatched > MAX_UNMATCHED_TARGETS:
                # Each failed search scans to the end of the line; past this many, protect the
                # rest of the line as written instead, which keeps the work linear and no
                # destination after this point can change.
                out.append(stash.put("t", line[pos:]))
                return "".join(out)
            out.append(line[pos:j + 2])  # an unmatched opener: keep looking for later links
            pos = j + 2
            continue
        value = line[j + 2:k - 1]
        out.append(line[pos:j + 2])
        if multiline_only and not 0 < value.count("\n") <= 2:
            out.append(value + ")")
        else:
            out.append(stash.put("t", value) + ")")
        pos = k
    out.append(line[pos:])
    return "".join(out)


def _url_token(match: re.Match, stash: Stash) -> str:
    """Stash the URL without trailing punctuation or unbalanced closing parentheses.

    Counts parentheses once and walks back by index, so a long run of ``)`` stays linear.
    """
    url = match.group(0)
    opens, closes = url.count("("), url.count(")")
    end = len(url)
    while end:
        ch = url[end - 1]
        if ch == ")" and closes > opens:
            closes -= 1
        elif ch not in URL_TRAILING:
            break
        end -= 1
    return stash.put("u", url[:end]) + url[end:]


def protect_code_spans(lines: list[str], stash: Stash, skip, starts_block=lambda line: False,
                       one_line_block=lambda line: False) -> list[str]:
    """Protect code spans, including spans that cross lines inside one run of text.

    Consecutive non-blank lines that *skip* rejects are matched together, so a span opened on
    one line and closed on a later one becomes a single token whose value holds the newlines.
    Link targets and HTML tags that cross lines are protected the same way. A run ends at a
    line that *starts_block* accepts (a heading, list item, quote or rule), and right after a
    line that *one_line_block* accepts (a heading), because inline content never crosses a
    block boundary.
    """
    out: list[str] = []
    group: list[str] = []

    def flush() -> None:
        if group:
            text = _protect_code_spans("\n".join(group), stash)
            if "](" in text:
                text = _protect_link_targets(text, stash, multiline_only=True)
            if "]:" in text:
                text = REF_DEF_NEXT_LINE_RE.sub(lambda m: m.group(1) + stash.put("t", m.group(2)), text)
            if "<" in text:
                text = HTML_TAG_MULTILINE_RE.sub(
                    lambda m: stash.put("h", m.group(0)) if "\n" in m.group(0) else m.group(0), text)
            out.extend(text.split("\n"))
            group.clear()

    for line in lines:
        if not line.strip() or skip(line):
            flush()
            out.append(line)
        else:
            if starts_block(line):
                flush()
            if one_line_block(line):
                group.append(line)
                flush()
                continue
            group.append(line)
    flush()
    return out


def _sub_outside_urls(pattern: re.Pattern, kind: str, line: str, stash: Stash, skip=None) -> str:
    """Stash *pattern* matches, except those starting inside a bare URL (URLs are stashed whole later)
    and those *skip* rejects."""
    if "://" not in line:
        return pattern.sub(lambda m: m.group(0) if skip and skip(m) else stash.put(kind, m.group(0)), line)
    starts = [m.span() for m in URL_RE.finditer(line)]
    ends = [end for _, end in starts]

    def put(m: re.Match) -> str:
        if skip and skip(m):
            return m.group(0)
        i = bisect.bisect_right(ends, m.start())
        if i < len(starts) and starts[i][0] <= m.start():
            return m.group(0)
        return stash.put(kind, m.group(0))

    return pattern.sub(put, line)


REF_DEF_RE = re.compile(r"^( {0,3}\[[^\]\n]+\]:[ \t]*)(<[^>\n]*>|\S+)")


def protect_cells(line: str, stash: Stash) -> str:
    """Protect row-local code first, then protect the remaining cells independently.

    A balanced code span makes its pipes literal, even with spaces around them. Unmatched
    backticks stay visible; they cannot pair with a backtick in another row. Other protected
    spans (URLs, link targets, math) must still stop at the remaining cell separators.
    """
    line = _protect_code_spans(line, stash)
    parts, start = [], 0
    for i, ch in enumerate(line):
        if ch == "|" and not _escaped(line, i):
            parts.extend((protect_inline(line[start:i], stash), "|"))
            start = i + 1
    parts.append(protect_inline(line[start:], stash))
    return "".join(parts)


def protect_inline(line: str, stash: Stash) -> str:
    """Protect inline code, inline display math, escapes, HTML tags, link targets and URLs."""
    ref = REF_DEF_RE.match(line)
    if ref:  # a reference definition (``[id]: /path``): its destination is a link target
        line = ref.group(1) + stash.put("t", ref.group(2)) + line[ref.end():]
    if "`" in line:
        line = _protect_code_spans(line, stash)
    if "$$" in line:
        line = _sub_outside_urls(INLINE_MATH_RE, "n", line, stash)
    if "<" in line:
        # Tags before escapes: a backslash inside an attribute does not escape its closing quote.
        # An escaped ``\<`` is not a tag.
        line = _sub_outside_urls(HTML_TAG_RE, "h", line, stash, skip=lambda m: _escaped(m.string, m.start()))
    if "\\" in line:
        line = _sub_outside_urls(ESCAPE_RE, "e", line, stash)
    if "](" in line:
        line = _protect_link_targets(line, stash)
    if "://" in line:
        line = URL_RE.sub(lambda m: _url_token(m, stash), line)
    return line
