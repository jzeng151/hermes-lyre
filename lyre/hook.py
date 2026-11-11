"""The ``transform_llm_output`` callback (spec: reply rewrite hook, #10).

Every final reply on a surface where Lyre is on is replaced by the formatter's output. Returning
``None`` leaves the reply unchanged; that is the answer whenever Lyre is off for the surface, the
formatter changed nothing, or anything failed, so Lyre can never cost the user a reply.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .formatter import format_for_speech
from .settings import load_settings

logger = logging.getLogger(__name__)

SLOW_MS = 200

_MARKDOWN_MESSAGING = frozenset({"telegram", "discord", "slack", "matrix", "teams", "mattermost", "google_chat"})
# platform -> (setting group, render profile); anything else is a messaging chat on the plain profile.
_SURFACES: dict[str, tuple[str, str]] = {
    "email": ("email", "plain"),
    "cli": ("cli", "plain"),
    "tui": ("tui", "plain"),
    "cron": ("cron", "plain"),
    "desktop": ("desktop", "markdown"),
    "api_server": ("api", "markdown"),
    "acp": ("api", "markdown"),
    "a2a": ("api", "markdown"),
    "webhook": ("api", "markdown"),
}
_NEVER = frozenset({"", "subagent"})


def surface(platform: str) -> tuple[str, str] | None:
    """(setting group, profile) for a ``platform`` value, or None where Lyre never runs."""
    name = (platform or "").strip().lower()
    if name in _NEVER:
        return None
    if name in _SURFACES:
        return _SURFACES[name]
    return ("messaging", "markdown" if name in _MARKDOWN_MESSAGING else "plain")


def rewrite(ctx, response_text: str, platform: str, turn_id: str = "") -> str | None:
    """Steps 1 to 5 of the spec's decision order. May raise; the hook catches."""
    resolved = surface(platform)
    if resolved is None or not isinstance(response_text, str):
        return None
    settings = load_settings(ctx)
    group, profile = resolved
    if not settings.enabled or not settings.groups.get(group, False):
        return None

    def failed(exc: Exception) -> None:
        # Called inside the formatter's except block, so exc_info carries the traceback (ADR 0005).
        logger.warning("lyre: rewrite skipped (%s) turn=%s", type(exc).__name__, turn_id, exc_info=True)

    start = time.perf_counter()
    result = format_for_speech(response_text, profile=profile, verbosity=settings.verbosity,
                               emoji_policy=settings.emoji_policy, table_style=settings.table_style,
                               on_error=failed)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if elapsed_ms > SLOW_MS:
        logger.info("lyre: formatting took %.0f ms for %d characters", elapsed_ms, len(response_text))
    if result == response_text or not result.strip():
        return None
    return result


def make_hook(ctx):
    """The callback registered with Hermes, bound to this plugin's context."""

    def transform_llm_output(response_text: str = "", platform: str = "", turn_id: str = "",
                             **kwargs: Any) -> str | None:
        try:
            return rewrite(ctx, response_text, platform, turn_id)
        except Exception as exc:  # Lyre must never cost the user a reply (ADR 0005)
            logger.warning("lyre: rewrite skipped (%s) turn=%s", type(exc).__name__, turn_id, exc_info=True)
            return None

    return transform_llm_output
