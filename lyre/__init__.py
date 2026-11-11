"""Lyre: Hermes replies, readable by ear."""

from __future__ import annotations

from .hook import transform_llm_output


def register(ctx) -> None:
    ctx.register_hook("transform_llm_output", transform_llm_output)
