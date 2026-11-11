"""Shared types for the speech formatter: options passed to rules and the blocks they receive."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Profile = Literal["plain", "markdown"]
Verbosity = Literal["brief", "normal", "full"]
EmojiPolicy = Literal["words", "remove", "keep"]
TableStyle = Literal["sentences", "unchanged"]

PROFILES = ("plain", "markdown")
VERBOSITIES = ("brief", "normal", "full")
EMOJI_POLICIES = ("words", "remove", "keep")
TABLE_STYLES = ("sentences", "unchanged")


@dataclass(frozen=True)
class Options:
    """Everything a rule may base its output on.

    ``latin`` is False when fewer than half of the letters outside protected spans are Latin
    script; rules must then insert no English words (spec: Script detection).
    """

    profile: Profile
    verbosity: Verbosity = "normal"
    emoji_policy: EmojiPolicy = "words"
    table_style: TableStyle = "sentences"
    latin: bool = True


@dataclass
class Block:
    """A run of lines the block pass grouped together.

    ``lines`` hold placeholder tokens in place of protected spans; a rule must keep every
    token it receives (the core restores them). ``kind`` is one of ``paragraph``, ``heading``,
    ``list``, ``table``, ``rule``, ``blockquote``, ``code``, ``math`` or ``blank``.
    ``meta`` carries kind-specific facts, documented on the producing function in ``blocks.py``.
    """

    kind: str
    lines: list[str]
    meta: dict[str, Any] = field(default_factory=dict)
