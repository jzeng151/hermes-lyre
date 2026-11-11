"""Settings: defaults, validation, round trip and the manifest schema (spec: settings, #11)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

import lyre
from lyre import settings
from lyre.settings import GROUPS, SCHEMA, load_settings, set_setting

MANIFEST = yaml.safe_load((Path(lyre.__file__).parent / "plugin.yaml").read_text(encoding="utf-8"))


class FakeConfigContext:
    """ctx.get_config / ctx.set_config over a dict, like plugins.entries.lyre.settings."""

    def __init__(self, values=None) -> None:
        self.values = dict(values or {})
        self.writes: list[tuple[str, object]] = []

    def get_config(self, key, default=None):
        return self.values.get(key, default)

    def set_config(self, key, value) -> None:
        self.writes.append((key, value))
        self.values[key] = value


@pytest.fixture(autouse=True)
def fresh_warnings():
    settings._warned.clear()
    yield
    settings._warned.clear()


def test_ac1_fresh_install_defaults():
    s = load_settings(FakeConfigContext())
    assert s.enabled is False
    assert dict(s.groups) == {"messaging": True, "email": True, "cli": True, "tui": True, "cron": True,
                              "desktop": False, "api": False}
    assert (s.verbosity, s.emoji_policy, s.table_style) == ("normal", "words", "sentences")


def test_ac2_invalid_choice_falls_back_with_one_warning(caplog):
    ctx = FakeConfigContext({"verbosity": "loud"})
    with caplog.at_level(logging.WARNING, logger="lyre.settings"):
        assert load_settings(ctx).verbosity == "normal"
        assert load_settings(ctx).verbosity == "normal"
    warnings = [r for r in caplog.records if "verbosity" in r.getMessage()]
    assert len(warnings) == 1
    assert "loud" not in warnings[0].getMessage()


@pytest.mark.parametrize("key,value", [
    ("enabled", "yes"), ("enabled", 1), ("messaging", "true"), ("verbosity", ""), ("verbosity", 3),
    ("emoji_policy", ["words"]), ("table_style", "Sentences"),
])
def test_wrong_types_and_values_give_default(key, value):
    s = load_settings(FakeConfigContext({key: value}))
    default = SCHEMA[key][1]
    actual = s.groups[key] if key in GROUPS else getattr(s, key)
    assert actual == default


def test_unknown_keys_are_ignored():
    assert load_settings(FakeConfigContext({"old_key": 1})) == load_settings(FakeConfigContext())


def test_read_failure_gives_defaults():
    class Broken(FakeConfigContext):
        def get_config(self, key, default=None):
            raise RuntimeError("config unreadable")

    assert load_settings(Broken()) == load_settings(FakeConfigContext())


def test_settings_are_read_live():
    ctx = FakeConfigContext()
    assert load_settings(ctx).enabled is False
    set_setting(ctx, "enabled", True)
    assert load_settings(ctx).enabled is True


@pytest.mark.parametrize("key,value", [("verbosity", "brief"), ("desktop", True), ("table_style", "unchanged")])
def test_round_trip(key, value):
    ctx = FakeConfigContext()
    set_setting(ctx, key, value)
    s = load_settings(ctx)
    assert (s.groups[key] if key in GROUPS else getattr(s, key)) == value


@pytest.mark.parametrize("key,value,fragment", [
    ("verbosity", "loud", "brief, normal, full"),
    ("enabled", "yes", "on or off"),
    ("volume", 3, "no setting called 'volume'"),
])
def test_ac6_invalid_write_raises_and_leaves_config(key, value, fragment):
    ctx = FakeConfigContext()
    with pytest.raises(ValueError, match=fragment):
        set_setting(ctx, key, value)
    assert ctx.writes == []


def test_manifest_schema_matches_code():
    schema = MANIFEST["config_schema"]
    assert list(schema) == list(SCHEMA)
    for key, (kind, default, choices) in SCHEMA.items():
        spec = schema[key]
        assert spec["type"] == {bool: "bool", str: "str"}[kind]
        assert spec["default"] == default
        assert tuple(spec.get("choices") or ()) == (choices or ())
        assert spec.get("label"), f"{key} needs a label for the Desktop form"
