"""The /a11y command (spec: /a11y command, #12)."""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

import lyre
from lyre import command
from lyre.hook import make_hook


class Ctx:
    def __init__(self, surface="cli", fail_on=(), **values) -> None:
        self.values = dict(values)
        self.writes: list[tuple[str, object]] = []
        self.surface = surface
        self.fail_on = set(fail_on)
        self.commands: dict = {}

    def get_config(self, key, default=None):
        return self.values.get(key, default)

    def set_config(self, key, value) -> None:
        if key in self.fail_on:
            raise OSError("disk full")
        self.writes.append((key, value))
        self.values[key] = value

    def session_surface(self) -> str:
        return self.surface

    def register_hook(self, *args, **kwargs) -> None:
        pass

    def register_command(self, name, handler, **kwargs) -> None:
        self.commands[name] = (handler, kwargs)


def a11y(ctx, args="", **kw):
    lyre.register(ctx)
    handler, _ = ctx.commands["a11y"]
    return handler(args, **kw)


GROUP = SimpleNamespace(chat_type="group")
DM = SimpleNamespace(chat_type="dm")


def test_registration():
    ctx = Ctx()
    lyre.register(ctx)
    _, kwargs = ctx.commands["a11y"]
    assert kwargs == {"description": command.DESCRIPTION, "args_hint": command.ARGS_HINT}


def test_ac1_on_in_telegram():
    ctx = Ctx(messaging=False)
    reply = a11y(ctx, "on", platform="telegram", source=DM)
    assert ctx.writes == [("messaging", True), ("enabled", True)]  # group first, master switch last
    assert reply == "Lyre is on. Replies in Telegram will be written for screen readers, starting with the next one."


def test_ac2_on_in_desktop_turns_on_desktop_and_rewrites_next_reply():
    ctx = Ctx(surface="desktop", enabled=True)
    a11y(ctx, "on", platform="local")
    assert ctx.writes == [("desktop", True)]
    assert make_hook(ctx)(response_text="| A |\n|---|\n| 1 |", platform="desktop").startswith("Table")


def test_ac3_off_keeps_groups():
    ctx = Ctx(enabled=True, desktop=True)
    assert a11y(ctx, "off", platform="cli") == "Lyre is off. Replies will be sent as written."
    assert ctx.writes == [("enabled", False)]
    assert ctx.values["desktop"] is True
    assert make_hook(ctx)(response_text="**x**", platform="cli") is None


@pytest.mark.parametrize("values,platform,expected", [
    ({}, "cli", "Lyre is off. Type /a11y on to turn it on."),
    ({"enabled": True}, "telegram", "Lyre is on for Telegram. Verbosity is normal."),
    ({"enabled": True, "verbosity": "full"}, "cli", "Lyre is on for the terminal. Verbosity is full."),
    ({"enabled": True}, "desktop",
     "Lyre is on, but off for the Desktop app. Type /a11y on here to include the Desktop app."),
    ({"enabled": True}, "subagent", "Lyre is on. Verbosity is normal."),
])
@pytest.mark.parametrize("args", ["", "status", "  STATUS  "])
def test_ac4_status_writes_nothing(values, platform, expected, args):
    ctx = Ctx(**values)
    assert a11y(ctx, args, platform=platform) == expected
    assert ctx.writes == []


def test_ac5_verbosity():
    ctx = Ctx()
    assert a11y(ctx, "verbosity full") == "Verbosity is now full."
    assert ctx.values["verbosity"] == "full"
    assert a11y(ctx, "verbosity loud") == "Verbosity must be brief, normal or full."
    assert a11y(ctx, "verbosity") == "Verbosity is full. Choose brief, normal or full."
    assert ctx.writes == [("verbosity", "full")]


@pytest.mark.parametrize("args", ["banana", "help", "on now", "verbosity full please", "status x"])
def test_ac6_usage(args):
    ctx = Ctx()
    assert a11y(ctx, args) == command.USAGE
    assert ctx.writes == []


@pytest.mark.parametrize("args", ["on", "off"])
def test_ac7_shared_chat_notice(args):
    assert a11y(Ctx(), args, platform="telegram", source=GROUP).endswith(command.SHARED)
    assert not a11y(Ctx(), args, platform="telegram", source=DM).endswith(command.SHARED)
    assert not a11y(Ctx(), args, platform="cli").endswith(command.SHARED)


def test_ac8_state_is_read_from_settings_each_time():
    ctx = Ctx()
    a11y(ctx, "on", platform="cli")
    restarted = Ctx(**ctx.values)  # a fresh process reads the same saved config
    assert a11y(restarted, "status", platform="cli") == "Lyre is on for the terminal. Verbosity is normal."


def test_ac9_replies_have_no_spoken_symbols():
    texts = [v for k, v in vars(command).items() if k.isupper() and isinstance(v, str) and k != "ARGS_HINT"]
    ctx = Ctx(messaging=False)
    for args, platform in [("on", "telegram"), ("status", "telegram"), ("off", "cli"), ("status", "desktop"),
                           ("verbosity", "cli"), ("verbosity loud", "cli"), ("x", "cli")]:
        texts.append(a11y(ctx, args, platform=platform, source=GROUP))
    for text in texts:
        assert not re.search(r"[*_#|`]", text), text
        assert all(ord(ch) < 0x2000 for ch in text), text


def test_ac11_failed_enabled_write_leaves_lyre_off():
    ctx = Ctx(messaging=False, fail_on={"enabled"})
    assert a11y(ctx, "on", platform="telegram") == "Lyre could not be turned on. Lyre is still off."
    assert ctx.values.get("enabled") is None
    assert make_hook(ctx)(response_text="**x**", platform="telegram") is None


def test_failed_group_write_changes_nothing():
    ctx = Ctx(enabled=True, fail_on={"desktop"})
    assert a11y(ctx, "on", platform="desktop") == "Lyre could not be turned on. Lyre is still on."
    assert ctx.writes == []


@pytest.mark.parametrize("args", ["off", "verbosity brief"])
def test_single_write_failure(args):
    ctx = Ctx(fail_on={"enabled", "verbosity"})
    assert a11y(ctx, args) == command.SAVE_FAILED


def test_on_twice_is_harmless():
    ctx = Ctx()
    first = a11y(ctx, "on", platform="cli")
    assert a11y(ctx, "on", platform="cli") == first
    assert ctx.writes == [("enabled", True)]


def test_session_surface_failure_drops_the_name():
    class Broken(Ctx):
        def session_surface(self):
            raise RuntimeError("no session")

    assert a11y(Broken(), "on", platform="local") == "Lyre is on."


def test_unknown_messaging_platform_name():
    assert "in New Chat will" in a11y(Ctx(), "on", platform="new_chat")
