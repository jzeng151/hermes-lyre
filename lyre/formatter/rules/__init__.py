"""Rule registry. Rule modules register themselves here when ``lyre.formatter`` is imported.

Block rules own one block kind and return the block's replacement lines. Inline rules rewrite
the text of paragraph, list, heading and table lines, one line at a time, in ``order``.
"""

from __future__ import annotations

from collections.abc import Callable

from ..model import Block, Options

InlineFn = Callable[[str], str]
BlockRule = Callable[[Block, Options, InlineFn], "list[str] | None"]
InlineRule = Callable[[str, Options], str]

_block_rules: dict[str, BlockRule] = {}
_inline_rules: list[tuple[int, str, InlineRule]] = []


def register_block_rule(kind: str, rule: BlockRule) -> None:
    """Make *rule* the owner of blocks of *kind*.

    The rule gets the block, the options and ``inline`` (applies every inline rule to one line
    of text) and returns replacement lines, or None to keep the block's default handling.
    Output lines must not contain newlines; returning ``[]`` removes the block.
    """
    if kind in _block_rules:
        raise ValueError(f"a block rule for {kind!r} is already registered")
    _block_rules[kind] = rule


def register_inline_rule(name: str, rule: InlineRule, order: int = 100) -> None:
    """Add an inline rule; lower ``order`` runs first. ``name`` must be unique."""
    if any(existing == name for _, existing, _ in _inline_rules):
        raise ValueError(f"an inline rule named {name!r} is already registered")
    _inline_rules.append((order, name, rule))
    _inline_rules.sort(key=lambda item: (item[0], item[1]))


def unregister(name_or_kind: str) -> None:
    """Remove a block rule (by kind) or inline rule (by name). Used by tests."""
    _block_rules.pop(name_or_kind, None)
    _inline_rules[:] = [item for item in _inline_rules if item[1] != name_or_kind]


def block_rule(kind: str) -> BlockRule | None:
    return _block_rules.get(kind)


def inline_rules() -> list[InlineRule]:
    return [rule for _, _, rule in _inline_rules]


_code_label: Callable[[str], object] | None = None


def register_code_label(match: Callable[[str], object]) -> None:
    """Recognize a code label line (``Python code, 1 line:``); the code it names follows it."""
    global _code_label
    _code_label = match


def is_code_label(line: str) -> bool:
    return bool(_code_label and _code_label(line.strip()))


def snapshot() -> tuple[dict, list]:
    """Copy of the registry, for tests that need it empty or altered."""
    return dict(_block_rules), list(_inline_rules)


def restore(saved: tuple[dict, list]) -> None:
    _block_rules.clear()
    _block_rules.update(saved[0])
    _inline_rules[:] = saved[1]


def clear() -> None:
    _block_rules.clear()
    _inline_rules.clear()
