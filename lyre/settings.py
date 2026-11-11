"""Lyre's settings: schema, validated reads and validated writes (spec: settings, #11).

Settings live at ``plugins.entries.lyre.settings.<key>`` and are read through the plugin
context on every call, never cached, so ``/a11y`` and the Desktop form apply to the next reply.
``SCHEMA`` mirrors ``config_schema`` in ``plugin.yaml``; a test keeps the two equal.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

logger = logging.getLogger(__name__)

GROUPS = ("messaging", "email", "cli", "tui", "cron", "desktop", "api")

# key -> (type, default, choices or None)
SCHEMA: Mapping[str, tuple[type, Any, tuple[str, ...] | None]] = MappingProxyType({
    "enabled": (bool, False, None),
    "messaging": (bool, True, None),
    "email": (bool, True, None),
    "cli": (bool, True, None),
    "tui": (bool, True, None),
    "cron": (bool, True, None),
    "desktop": (bool, False, None),
    "api": (bool, False, None),
    "verbosity": (str, "normal", ("brief", "normal", "full")),
    "emoji_policy": (str, "words", ("words", "remove", "keep")),
    "table_style": (str, "sentences", ("sentences", "unchanged")),
})

_warned: set[str] = set()  # keys already reported as invalid in this process (one warning each)


@dataclass(frozen=True)
class LyreSettings:
    enabled: bool
    groups: Mapping[str, bool]
    verbosity: str
    emoji_policy: str
    table_style: str


def _valid(key: str, value: Any) -> bool:
    kind, _, choices = SCHEMA[key]
    # bool is a subclass of int, and str never is; an exact type check rejects "yes" and 1 alike.
    if type(value) is not kind:
        return False
    return choices is None or value in choices


def _read(ctx, key: str) -> Any:
    _, default, _ = SCHEMA[key]
    try:
        value = ctx.get_config(key, default=default)
    except Exception:  # health: allow broad-except -- settings reads must never raise into the hook
        logger.warning("lyre: could not read setting %s; using default %r", key, default, exc_info=True)
        return default
    if value is None or _valid(key, value):
        return default if value is None else value
    if key not in _warned:
        _warned.add(key)
        logger.warning("lyre: setting %s has invalid value; using default %r", key, default)
    return default


def load_settings(ctx) -> LyreSettings:
    """Every setting, validated. Never raises; an invalid or missing value gives its default."""
    values = {key: _read(ctx, key) for key in SCHEMA}
    return LyreSettings(
        enabled=values["enabled"],
        groups=MappingProxyType({group: values[group] for group in GROUPS}),
        verbosity=values["verbosity"],
        emoji_policy=values["emoji_policy"],
        table_style=values["table_style"],
    )


def set_setting(ctx, key: str, value: Any) -> None:
    """Validate, then write one setting. Raises ValueError with a sentence the user can act on."""
    if key not in SCHEMA:
        raise ValueError(f"Lyre has no setting called {key!r}. Settings are: {', '.join(SCHEMA)}.")
    if not _valid(key, value):
        kind, _, choices = SCHEMA[key]
        allowed = ", ".join(choices) if choices else ("on or off" if kind is bool else kind.__name__)
        raise ValueError(f"{value!r} is not a valid value for {key}. Use {allowed}.")
    ctx.set_config(key, value)
