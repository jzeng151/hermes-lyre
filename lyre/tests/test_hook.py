"""The reply rewrite hook (spec: reply rewrite hook, #10)."""

from __future__ import annotations

import logging
import time

import pytest

import lyre
from lyre import hook

REPLY = "## Done\n\n**Build** passed ✅"
TABLE = "| Name | Price |\n|---|---|\n| Alpha | $10 |"


class Ctx:
    def __init__(self, **values) -> None:
        self.values = values
        self.hooks: dict = {}

    def get_config(self, key, default=None):
        return self.values.get(key, default)

    def set_config(self, key, value) -> None:
        self.values[key] = value

    def register_hook(self, name, callback, **kwargs) -> None:
        self.hooks[name] = callback

    def register_command(self, *args, **kwargs) -> None:
        pass


def callback(**settings):
    ctx = Ctx(**settings)
    lyre.register(ctx)
    return ctx, ctx.hooks["transform_llm_output"]


@pytest.mark.parametrize("platform", ["telegram", "whatsapp", "email", "cli", "tui", "cron", "desktop", "newchat"])
def test_ac1_off_returns_none(platform):
    _, cb = callback()
    assert cb(response_text=REPLY, platform=platform) is None


@pytest.mark.parametrize("platform", ["subagent", "", "SUBAGENT"])
def test_ac2_never_for_subagents_or_missing_platform(platform):
    _, cb = callback(enabled=True, desktop=True, api=True)
    assert cb(response_text=REPLY, platform=platform) is None


@pytest.mark.parametrize("platform,profile", [
    ("telegram", "markdown"), ("whatsapp", "plain"), ("email", "plain"), ("cli", "plain"), ("tui", "plain"),
    ("cron", "plain"), ("Telegram", "markdown"), ("google_chat", "markdown"), ("signal", "plain"),
])
def test_ac3_default_surfaces_rewrite_with_their_profile(platform, profile):
    _, cb = callback(enabled=True)
    out = cb(response_text=REPLY, platform=platform)
    expected = lyre.formatter.format_for_speech(REPLY, profile=profile)
    assert out == expected
    assert ("**" in out) == (profile == "markdown")


@pytest.mark.parametrize("platform", ["desktop", "api_server", "acp", "a2a", "webhook"])
def test_ac3_off_by_default_surfaces(platform):
    _, cb = callback(enabled=True)
    assert cb(response_text=REPLY, platform=platform) is None


@pytest.mark.parametrize("platform,group", [("desktop", "desktop"), ("api_server", "api"), ("acp", "api")])
def test_opt_in_surfaces(platform, group):
    _, cb = callback(enabled=True, **{group: True})
    assert cb(response_text=TABLE, platform=platform).startswith("Table, 1 row")


def test_group_switch_off():
    _, cb = callback(enabled=True, messaging=False)
    assert cb(response_text=REPLY, platform="telegram") is None
    assert cb(response_text=REPLY, platform="cli") is not None


def test_ac4_nothing_to_change_returns_none():
    _, cb = callback(enabled=True)
    assert cb(response_text="Plain words, nothing else.", platform="cli") is None


def test_ac5_exception_returns_none_and_logs_no_reply_text(monkeypatch, caplog):
    def boom(text, **kwargs):
        raise RuntimeError("formatter broke")

    monkeypatch.setattr(hook, "format_for_speech", boom)
    _, cb = callback(enabled=True)
    secret = "SECRET-REPLY-MARKER **x**"
    with caplog.at_level(logging.WARNING, logger="lyre.hook"):
        assert cb(response_text=secret, platform="cli", turn_id="t-42") is None
    records = [r for r in caplog.records if r.name == "lyre.hook"]
    assert len(records) == 1
    assert "RuntimeError" in records[0].getMessage() and "turn=t-42" in records[0].getMessage()
    assert "SECRET-REPLY-MARKER" not in caplog.text
    assert records[0].exc_info is not None  # ADR 0005: traceback kept, reply not in it


def test_ac6_settings_apply_to_the_next_reply():
    ctx, cb = callback(enabled=True)
    assert cb(response_text=REPLY, platform="cli") is not None
    ctx.set_config("enabled", False)
    assert cb(response_text=REPLY, platform="cli") is None
    ctx.set_config("enabled", True)
    ctx.set_config("verbosity", "full")
    assert cb(response_text="# Title", platform="cli") == "Heading: Title."


def test_ac7_unknown_platform_is_plain_messaging():
    _, cb = callback(enabled=True)
    assert cb(response_text=REPLY, platform="newchat") == lyre.formatter.format_for_speech(REPLY, profile="plain")


def test_ac8_twenty_kb_under_50_ms():
    _, cb = callback(enabled=True)
    block = REPLY + "\n\n" + TABLE + "\n\n- one\n- two\n\n[docs](https://x.test/a?b=1)\n\n"
    text = (block * (20_000 // len(block) + 1))[:20_000]
    cb(response_text=text, platform="cli")  # warm the rule registry and regex caches
    start = time.perf_counter()
    cb(response_text=text, platform="cli")
    assert time.perf_counter() - start < 0.05


@pytest.mark.parametrize("stub", ["", "   ", "\n"])
def test_ac11_empty_result_returns_none(monkeypatch, stub):
    monkeypatch.setattr(hook, "format_for_speech", lambda text, **kwargs: stub)
    _, cb = callback(enabled=True)
    assert cb(response_text=REPLY, platform="cli") is None


def test_ac11_emoji_only_reply_returns_none():
    _, cb = callback(enabled=True)
    assert cb(response_text="🎉", platform="telegram") is None


def test_settings_passed_to_formatter(monkeypatch):
    seen = {}

    def spy(text, **kwargs):
        seen.update(kwargs)
        return text + " changed"

    monkeypatch.setattr(hook, "format_for_speech", spy)
    _, cb = callback(enabled=True, verbosity="brief", emoji_policy="keep", table_style="unchanged")
    cb(response_text=REPLY, platform="whatsapp")
    assert callable(seen.pop("on_error"))
    assert seen == {"profile": "plain", "verbosity": "brief", "emoji_policy": "keep", "table_style": "unchanged"}


def test_slow_format_logs_info_without_text(monkeypatch, caplog):
    ticks = iter([0.0, 0.5])
    monkeypatch.setattr(hook.time, "perf_counter", lambda: next(ticks))
    _, cb = callback(enabled=True)
    with caplog.at_level(logging.INFO, logger="lyre.hook"):
        cb(response_text=REPLY, platform="cli")
    assert "500 ms" in caplog.text and "Build" not in caplog.text


def test_failing_rule_inside_the_formatter_is_logged(caplog):
    from lyre.formatter import rules

    def boom(text, opts):
        raise RuntimeError("rule broke")

    saved = rules.snapshot()
    rules.register_inline_rule("boom", boom, order=1)
    try:
        _, cb = callback(enabled=True)
        with caplog.at_level(logging.WARNING, logger="lyre.hook"):
            assert cb(response_text="SECRET-MARKER **x**", platform="cli", turn_id="t-7") is None
    finally:
        rules.restore(saved)
    records = [r for r in caplog.records if r.name == "lyre.hook"]
    assert len(records) == 1 and records[0].exc_info is not None
    assert "RuntimeError" in records[0].getMessage() and "turn=t-7" in records[0].getMessage()
    assert "SECRET-MARKER" not in caplog.text
