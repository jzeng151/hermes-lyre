"""The ``/a11y`` command (spec: /a11y command, #12).

Turns Lyre on and off, reports its state and sets verbosity from any chat or terminal. Command
replies do not pass through the reply hook, so every reply here is a plain sentence: no
markdown, no emoji. Settings are profile-wide; the reply says so in shared chats.
"""

from __future__ import annotations

import logging
from typing import Any

from .hook import surface
from .settings import SCHEMA, load_settings, set_setting

logger = logging.getLogger(__name__)

DESCRIPTION = "Screen-reader friendly replies: on, off, status, verbosity"
ARGS_HINT = "on | off | status | verbosity brief|normal|full"

USAGE = "Usage: /a11y on, /a11y off, /a11y status, or /a11y verbosity followed by brief, normal or full."
SHARED = "This setting applies to every chat on this Hermes profile."
SAVE_FAILED = "Lyre could not save that setting. Nothing changed."
LEVELS: tuple[str, ...] = SCHEMA["verbosity"][2] or ()

_NAMES = {
    "telegram": "Telegram", "whatsapp": "WhatsApp", "whatsapp_cloud": "WhatsApp", "discord": "Discord",
    "slack": "Slack", "signal": "Signal", "matrix": "Matrix", "teams": "Teams", "mattermost": "Mattermost",
    "google_chat": "Google Chat", "sms": "SMS", "irc": "IRC", "qqbot": "QQ", "wecom": "WeCom",
    "email": "email", "cli": "the terminal", "tui": "the terminal UI", "cron": "scheduled tasks",
    "desktop": "the Desktop app", "api_server": "API and editor sessions", "acp": "API and editor sessions",
    "a2a": "API and editor sessions", "webhook": "API and editor sessions",
}


def _caller(ctx, platform: str) -> tuple[str | None, str | None]:
    """(setting group, readable surface name) of the caller, or (None, None) when unknown."""
    name = (platform or "").strip().lower()
    if name in ("", "local"):
        try:
            name = (ctx.session_surface() or "").strip().lower()
        except Exception:  # health: allow broad-except -- an unknown surface only drops the name
            logger.warning("lyre: could not read the session surface", exc_info=True)
            name = ""
    resolved = surface(name)
    if resolved is None:
        return None, None
    return resolved[0], _NAMES.get(name, name.replace("_", " ").title())


def _shared(source: Any) -> bool:
    chat_type = getattr(source, "chat_type", None) if source is not None else None
    return bool(chat_type) and chat_type != "dm"


def _write(ctx, key: str, value: Any) -> bool:
    try:
        set_setting(ctx, key, value)
    except Exception as exc:  # a failed write becomes a plain reply, never a traceback in chat
        logger.warning("lyre: could not save setting %s (%s)", key, type(exc).__name__, exc_info=True)
        return False
    return True


def _status(ctx, group: str | None, name: str | None) -> str:
    settings = load_settings(ctx)
    if not settings.enabled:
        return "Lyre is off. Type /a11y on to turn it on."
    if group is None:
        return f"Lyre is on. Verbosity is {settings.verbosity}."
    if settings.groups.get(group, False):
        return f"Lyre is on for {name}. Verbosity is {settings.verbosity}."
    return f"Lyre is on, but off for {name}. Type /a11y on here to include {name}."


def _turn_on(ctx, group: str | None, name: str | None) -> str:
    settings = load_settings(ctx)
    still = "Lyre is still on." if settings.enabled else "Lyre is still off."
    # The group first, the master switch last: a failure never leaves Lyre on without this surface.
    if group is not None and not settings.groups.get(group, False) and not _write(ctx, group, True):
        return f"Lyre could not be turned on. {still}"
    if not settings.enabled and not _write(ctx, "enabled", True):
        return f"Lyre could not be turned on. {still}"
    if name is None:
        return "Lyre is on."
    return f"Lyre is on. Replies in {name} will be written for screen readers, starting with the next one."


def _verbosity(ctx, words: list[str]) -> str:
    if not words:
        return f"Verbosity is {load_settings(ctx).verbosity}. Choose brief, normal or full."
    if len(words) > 1:
        return USAGE
    if words[0] not in LEVELS:
        return "Verbosity must be brief, normal or full."
    return f"Verbosity is now {words[0]}." if _write(ctx, "verbosity", words[0]) else SAVE_FAILED


def run(ctx, raw_args: str, platform: str = "", source: Any = None) -> str:
    words = (raw_args or "").strip().lower().split()
    command, rest = (words[0], words[1:]) if words else ("status", [])
    if command == "verbosity":
        return _verbosity(ctx, rest)
    if rest or command not in ("status", "on", "off"):
        return USAGE
    group, name = _caller(ctx, platform)
    if command == "status":
        return _status(ctx, group, name)
    if command == "on":
        reply = _turn_on(ctx, group, name)
    else:
        reply = "Lyre is off. Replies will be sent as written." if _write(ctx, "enabled", False) else SAVE_FAILED
    return f"{reply} {SHARED}" if _shared(source) else reply


def make_command(ctx):
    """The ``/a11y`` handler registered with Hermes, bound to this plugin's context."""

    def handle_a11y(raw_args: str = "", *, platform: str = "", source: Any = None, **kwargs: Any) -> str:
        try:
            return run(ctx, raw_args, platform, source)
        except Exception:  # health: allow broad-except -- the user always gets a sentence back
            logger.warning("lyre: /a11y failed", exc_info=True)
            return SAVE_FAILED

    return handle_a11y
