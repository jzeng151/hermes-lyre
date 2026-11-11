"""Round trip through each Hermes platform formatter (#13, AC-14; T13).

Hermes runs Lyre's rewrite first, then the adapter's own ``format_message``, then splits long
messages. These tests run real adapter code, so they need Hermes importable: they skip in the
plain test job and run in the CI job that installs Hermes.

Adapters are built with ``object.__new__``: ``format_message`` only formats text, and building an
adapter normally would need a live connection.
"""

from __future__ import annotations

import importlib
import re
from collections import Counter
from typing import cast

import pytest

from lyre.formatter import format_for_speech
from lyre.formatter.model import Profile
from lyre.hook import surface

base = pytest.importorskip("gateway.platforms.base", reason="needs Hermes installed")
helpers = pytest.importorskip("gateway.platforms.helpers", reason="needs Hermes installed")

ADAPTERS = {
    "telegram": ("plugins.platforms.telegram.adapter", "TelegramAdapter"),
    "discord": ("plugins.platforms.discord.adapter", "DiscordAdapter"),
    "slack": ("plugins.platforms.slack.adapter", "SlackAdapter"),
    "whatsapp": ("plugins.platforms.whatsapp.adapter", "WhatsAppAdapter"),
}

STATUS = "Release notes \u2705 shipped, \u26a0\ufe0f one warning, \u274c one failure, \u23f3 one pending."
TABLE = "| Name | Price | Stock |\n|---|---|---|\n" + "\n".join(
    f"| Item {i} | ${i}.00 | {i * 3} |" for i in range(1, 41))
CODE = "Run this:\n\n```py\nprint('report | done')\nresult = total + 1\n```\n\nThen check the output."
CURATED = [
    STATUS,
    TABLE,
    CODE,
    "## Summary\n\nThe **deploy** finished. See [the run](https://ci.example.test/runs/1234?x=1&y=2).",
    "1. Build\n2. Test\n   - unit\n   - integration\n3. Ship \U0001f680",
    "> Note: the cache is *warm*.\n\nUse `make clean` first.",
    "# Weekly report\n\n🎉 All **12** jobs passed.\n\n| Job | Result |\n|---|---|\n| build | ✅ |\n| lint | ❌ |",
    "Steps:\n\n- Open `config.yaml`\n- Set `retries: 3`\n- Run:\n\n  ```bash\n  make deploy\n  ```",
    "~~Old plan~~ New plan: use _staging_ first, then https://example.test/deploy?env=prod&id=7.",
]
REPLIES = CURATED


def _adapter(platform: str):
    module, name = ADAPTERS[platform]
    try:
        cls = getattr(importlib.import_module(module), name)
    except ImportError as exc:  # an optional platform dependency is missing
        pytest.skip(f"{platform} adapter not importable: {exc}")
        raise  # unreachable: skip raises
    return cls, object.__new__(cls)


def _lyre(text: str, platform: str) -> str:
    resolved = surface(platform)
    assert resolved is not None and resolved[0] == "messaging"
    return format_for_speech(text, profile=cast(Profile, resolved[1]))


def _shown(platform: str, text: str) -> str:
    """What the user sees: Telegram's MarkdownV2 escapes are not displayed."""
    return re.sub(r"\\(.)", r"\1", text) if platform == "telegram" else text


def _words(text: str) -> Counter:
    """Words as heard: a fence's language tag is markup (Lyre's code label names the language)."""
    text = re.sub(r"^\s*(```|~~~)[^\n]*$", " ", text, flags=re.M)
    return Counter(re.findall(r"[A-Za-z0-9]+", text))


def _outside_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", " ", text)


def _code_bodies(text: str) -> list[str]:
    return re.findall(r"```[^\n]*\n(.*?)\n```", text, flags=re.S)


@pytest.mark.parametrize("platform", list(ADAPTERS))
@pytest.mark.parametrize("index", range(len(REPLIES)))
def test_adapter_keeps_every_word_and_code(platform, index):
    cls, adapter = _adapter(platform)
    ours = _lyre(REPLIES[index], platform)
    final = _shown(platform, cls.format_message(adapter, ours))
    missing = _words(ours) - _words(final)
    assert not missing, f"{platform} dropped {sorted(missing)[:5]} (reply {index})"
    for body in _code_bodies(ours):
        assert body in final, f"{platform} changed code (reply {index})"


@pytest.mark.parametrize("platform", list(ADAPTERS))
@pytest.mark.parametrize("index", range(len(REPLIES)))
def test_adapter_adds_no_spoken_symbols_outside_code(platform, index):
    cls, adapter = _adapter(platform)
    ours = _lyre(REPLIES[index], platform)
    final = _outside_code(_shown(platform, cls.format_message(adapter, ours)))
    before = _outside_code(ours)
    assert "|---" not in final

    def headings(text: str) -> int:
        return sum(line.startswith("#") for line in text.split("\n"))

    assert headings(final) <= headings(before), f"{platform} added a heading line (reply {index})"
    # Adapters turn Markdown into their own markup (``**b**`` to ``*b*``, ``*i*`` to ``_i_``),
    # which the app displays as formatting. They must not add more of these characters than
    # Lyre left, or the reader hears the extra ones.
    for symbols in ("*_", "~", "|"):
        added = sum(final.count(c) for c in symbols) - sum(before.count(c) for c in symbols)
        assert added <= 0, f"{platform} added {symbols!r} (reply {index})"


@pytest.mark.parametrize("platform,limit", [("telegram", 4096), ("discord", 2000)])
def test_long_spoken_table_splits_without_losing_words(platform, limit):
    cls, adapter = _adapter(platform)
    assert cls.MAX_MESSAGE_LENGTH == limit
    ours = _lyre(TABLE + "\n\n" + TABLE.replace("Item", "Part"), platform)
    final = cls.format_message(adapter, ours)
    len_fn = base.utf16_len if platform == "telegram" else None
    chunks = base.BasePlatformAdapter.truncate_message(final, limit, len_fn=len_fn)
    measure = len_fn or len
    assert all(measure(chunk) <= limit for chunk in chunks)
    joined = _shown(platform, "\n".join(chunks))
    assert not _words(_shown(platform, final)) - _words(joined)
    if len(chunks) > 1:  # Hermes appends a split marker such as (1/2) to each chunk
        assert all(f"({i}/{len(chunks)})" in chunk for i, chunk in enumerate(chunks, 1))


def test_ac14_status_words_survive_core_plain_text_formatter():
    """Core's plain-text formatter (SMS, iMessage, BlueBubbles) after Lyre keeps the words."""
    ours = format_for_speech(STATUS + "\n\n" + CODE, profile="plain")
    final = helpers.strip_markdown(ours)
    for word in ("(done)", "(warning)", "(failed)", "(pending)"):
        assert word in final
    assert "print('report | done')" in final and "result = total + 1" in final


@pytest.mark.xfail(strict=True, reason="core's strip_markdown also strips ** inside code; Lyre cannot prevent it")
def test_core_plain_text_formatter_keeps_markers_inside_code():
    ours = format_for_speech("```py\nx = '**literal**'\n```", profile="plain")
    assert "x = '**literal**'" in helpers.strip_markdown(ours)
