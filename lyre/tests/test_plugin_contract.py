"""Contract tests: the manifest matches what register() does, and the plugin stays stdlib-only."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from typing import Any

import yaml

import lyre
from lyre import hook

PLUGIN_DIR = Path(lyre.__file__).parent
MANIFEST = yaml.safe_load((PLUGIN_DIR / "plugin.yaml").read_text(encoding="utf-8"))


class FakeContext:
    """Records every ctx.register_* call register() makes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        if not name.startswith("register_"):
            raise AttributeError(name)

        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return record

    def names(self, kind: str) -> list[str]:
        return [args[0] for call, args, _ in self.calls if call == kind]


def _registered() -> FakeContext:
    ctx = FakeContext()
    lyre.register(ctx)
    return ctx


def test_manifest_identity():
    assert MANIFEST["name"] == "lyre"
    assert MANIFEST["requires_hermes"] == ">=0.23.0"


def test_declared_hooks_match_registrations():
    assert sorted(_registered().names("register_hook")) == sorted(MANIFEST.get("provides_hooks", []))


def test_registers_no_tools_or_middleware():
    ctx = _registered()
    assert not MANIFEST.get("provides_tools")
    assert not MANIFEST.get("provides_middleware")
    assert ctx.names("register_tool") == []
    assert ctx.names("register_middleware") == []


def test_no_stream_hold():
    for call, _, kwargs in _registered().calls:
        if call == "register_hook":
            assert not kwargs.get("hold_stream"), "Lyre must not hold the stream"


def test_hook_accepts_full_payload_and_is_off_by_default():
    ctx = _registered()
    ctx.get_config = lambda key, default=None: default  # fresh install: no settings written
    (callback,) = [args[1] for call, args, _ in ctx.calls if call == "register_hook"]
    params = inspect.signature(callback).parameters.values()
    assert any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params)
    payload: dict[str, Any] = dict(response_text="**Done** ✅", session_id="s", model="m",
                                   platform="telegram", turn_id="t", some_future_field=1)
    assert callback(**payload) is None
    assert hook.surface("telegram") == ("messaging", "markdown")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_standard_library_only():
    for path in PLUGIN_DIR.rglob("*.py"):
        if "tests" in path.relative_to(PLUGIN_DIR).parts:
            continue
        outside = {m for m in _imported_modules(path) if m not in sys.stdlib_module_names}
        assert not outside, f"{path.relative_to(PLUGIN_DIR)} imports non-stdlib modules: {sorted(outside)}"


def test_registers_the_write_for_ears_skill():
    (call,) = [(args, kwargs) for name, args, kwargs in _registered().calls if name == "register_skill"]
    args, kwargs = call
    name, path = args
    assert name == "write-for-ears"
    assert Path(path).is_file()
    assert kwargs["description"]
    text = Path(path).read_text(encoding="utf-8")
    front = yaml.safe_load(text.split("---")[1])
    assert front["name"] == name and front["description"].startswith("Use when")


def test_skill_is_written_for_ears():
    """The skill follows its own advice: no emoji, no tables, headings in order."""
    text = lyre.SKILL_PATH.read_text(encoding="utf-8")
    body = text.split("---", 2)[2]
    assert all(ord(ch) < 0x2000 for ch in body), "no emoji or symbols"
    assert "|---" not in body
    levels = [len(line) - len(line.lstrip("#")) for line in body.splitlines() if line.startswith("#")]
    assert levels[0] == 1 and all(b - a <= 1 for a, b in zip(levels, levels[1:]))
