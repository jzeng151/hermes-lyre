"""Lyre: Hermes replies, readable by ear."""

from __future__ import annotations

from pathlib import Path

from .command import ARGS_HINT, DESCRIPTION, make_command
from .hook import make_hook

SKILL = "write-for-ears"
SKILL_PATH = Path(__file__).parent / "skills" / SKILL / "SKILL.md"
SKILL_DESCRIPTION = "Write long documents for someone using a screen reader: headings, short paragraphs, plain links."


def register(ctx) -> None:
    ctx.register_hook("transform_llm_output", make_hook(ctx))
    ctx.register_command("a11y", handler=make_command(ctx), description=DESCRIPTION, args_hint=ARGS_HINT)
    ctx.register_skill(SKILL, SKILL_PATH, description=SKILL_DESCRIPTION)
