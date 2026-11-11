"""Lyre: Hermes replies, readable by ear."""

from __future__ import annotations

from .command import ARGS_HINT, DESCRIPTION, make_command
from .hook import make_hook


def register(ctx) -> None:
    ctx.register_hook("transform_llm_output", make_hook(ctx))
    ctx.register_command("a11y", handler=make_command(ctx), description=DESCRIPTION, args_hint=ARGS_HINT)
