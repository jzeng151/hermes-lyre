"""Lyre: Hermes replies, readable by ear."""

from __future__ import annotations

from .hook import make_hook


def register(ctx) -> None:
    ctx.register_hook("transform_llm_output", make_hook(ctx))
