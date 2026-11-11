"""R7: code blocks are announced before and after (both profiles).

``Python code, 12 lines:`` before a block and ``End of code.`` after it; the code itself is a
protected span and never changes. Fences are kept on every profile until the baseline test
(#2) settles spec Q1. A block that already has Lyre's labels around it gets none added, so a
second pass changes nothing. Unclosed fences and mostly non-Latin replies get no labels.
"""

from __future__ import annotations

import re

from ..model import Block, Options
from . import InlineFn, register_block_rule, register_code_label

LANGUAGES = {
    "python": "Python", "py": "Python", "javascript": "JavaScript", "js": "JavaScript",
    "typescript": "TypeScript", "ts": "TypeScript", "bash": "Bash", "sh": "Shell", "shell": "Shell",
    "zsh": "Shell", "console": "Shell", "json": "JSON", "yaml": "YAML", "yml": "YAML", "sql": "SQL",
    "rust": "Rust", "rs": "Rust", "go": "Go", "golang": "Go", "java": "Java", "c": "C", "cpp": "C++",
    "c++": "C++", "csharp": "C#", "cs": "C#", "c#": "C#", "ruby": "Ruby", "rb": "Ruby", "php": "PHP",
    "html": "HTML", "css": "CSS", "markdown": "Markdown", "md": "Markdown", "diff": "Diff",
}
LABEL_RE = re.compile(r"^(?:[A-Z][\w#+]*(?: [\w#+]+)* code|Code)(?:, \d+ lines?)?:$")
END = "End of code."
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")


def _describe(original: str, token_kind: str) -> tuple[str, int] | None:
    """(language name or "", content line count), or None for an unclosed fence."""
    lines = original.split("\n")
    if token_kind != "f":
        return "", len(lines)
    opening = _FENCE_RE.match(lines[0])
    fence = opening.group(1) if opening else "```"
    body = lines[-1].strip()
    if len(lines) < 2 or not (len(body) >= len(fence) and body == fence[0] * len(body)):
        return None
    info = (opening.group(2).strip().split() or [""])[0].lower() if opening else ""
    return LANGUAGES.get(info, ""), len(lines) - 2


def _label(language: str, count: int, opts: Options) -> str:
    if opts.verbosity == "brief":
        return "Code:"
    name = f"{language} code" if language else "Code"
    return f"{name}, {count} line{'' if count == 1 else 's'}:"


def labelled(line: str, opts: Options) -> list[str] | None:
    """*line* (one code token line) with its labels, or None when it gets none.

    Also used by the list rule for code inside list items, which the list rule owns.
    """
    token = line.strip()
    if token[1] not in "fc":
        return None  # display math and other block tokens are not code
    original = opts.span(token) if opts.span and opts.latin else None
    if original is None:
        return None
    described = _describe(original, token[1])
    if described is None:
        return None
    label = _label(*described, opts)
    if token[1] == "c":
        # A label line directly above indented code would make markdown read the code as part
        # of the paragraph, so indented code sits between blank lines.
        return [label, "", line, "", END]
    return [label, line, END]


def already_labelled(prev: str | None, nxt: str | None) -> bool:
    return prev is not None and bool(LABEL_RE.match(prev.strip())) and nxt is not None and nxt.strip() == END


def code(block: Block, opts: Options, inline: InlineFn) -> list[str] | None:
    if block.kind != "code" or already_labelled(block.meta.get("prev_text"), block.meta.get("next_text")):
        return None
    return labelled(block.lines[0], opts)


register_block_rule("code", code)
register_code_label(LABEL_RE.match)
