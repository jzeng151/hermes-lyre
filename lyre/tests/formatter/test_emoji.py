"""R4 emoji (task T4)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

ZWJ = "\u200d"

CASES = [
    ("✅ ASPTT : accusé reçu", "(done) ASPTT : accusé reçu"),
    ("⚠️ Check transport", "(warning) Check transport"),
    ("🔴 Pending", "(red) Pending"),
    ("🟡 slow, 🟢 fine, ⏳ queued", "(yellow) slow, (green) fine, (pending) queued"),
    ("❌ broke ✖️ 🚫", "(failed) broke (failed) (failed)"),
    ("✔️ ok ☑️", "(done) ok (done)"),
    ("✅", "(done)"),
    ("⚠\ufe0e", "(warning)"),
    ("✅⚠️🔴", "(done) (warning) (red)"),
    ("✅ 🎉 ⚠️ 🔴", "(done) (warning) (red)"),
    ("✅🎉", "(done)"),
    ("🎉 Hello", "Hello"),
    ("Hello 🎉 world", "Hello world"),
    ("Hello 🎉🎊  world 🎉", "Hello world"),
    ("Done 🎉.", "Done."),
    ("Status ✅", "Status (done)"),
    (f"👩🏽{ZWJ}💻 Family 👨{ZWJ}👩{ZWJ}👧{ZWJ}👦 1️⃣ #️⃣ *️⃣ 🏳️{ZWJ}🌈", "Family"),
    ("👍🏽 Text ✨\ufe0e", "Text"),
    (f"🙂{ZWJ}↔️ Hello 🙂{ZWJ}↕️", "Hello"),
    ("🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f Hello", "Hello"),
    ("🇯🇵 Tokyo", "Tokyo"),
    ("  🎉 Indented  prose\n  🎉 Child", "  Indented  prose\n  Child"),
    ("* 🎉 First\n* ⚠️ Second", "* First\n* (warning) Second"),
    ("Heading\n🎉\nNext", "Heading\nNext"),
    ("2 * 3 ✅ ©️ © ↔ ↔️ ⭐ x", "2 * 3 (done) © ↔ x"),
]


@pytest.mark.parametrize("text,expected", CASES)
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_words_policy(text, expected, profile):
    if profile == "markdown" and "*" in text:
        pytest.skip("markdown profile keeps list markers and emphasis; covered elsewhere")
    assert format_for_speech(text, profile=profile) == expected


@pytest.mark.parametrize("text", [
    "`✅ code` and ```🎉```",
    "https://example.test/🎉/a_✅?x=1",
    "```\nprint('✅ 🎉')\n```",
    "plain text, no emoji",
])
def test_protected_and_emoji_free_text_untouched(text):
    assert format_for_speech(text, profile="plain") is text


def test_emoji_only_reply_falls_back_to_input():
    assert format_for_speech("🎉 🎊", profile="plain") == "🎉 🎊"


def test_link_label_keeps_url_emoji():
    out = format_for_speech("🎉 [details](https://example.test/a_✅?x=1)", profile="plain")
    assert out == "[details](https://example.test/a_✅?x=1)"


def test_remove_policy_drops_status_emoji_too():
    assert format_for_speech("✅ done 🎉 now", profile="plain", emoji_policy="remove") == "done now"


def test_keep_policy_skips_the_rule():
    text = "✅ done 🎉"
    assert format_for_speech(text, profile="plain", emoji_policy="keep") is text


def test_non_latin_reply_keeps_status_emoji_and_drops_decoration():
    assert format_for_speech("Привет ✅ 🎉 мир", profile="plain") == "Привет ✅ мир"


def test_exposed_list_marker_after_removal_is_guarded():
    assert format_for_speech("🎉 1. Done", profile="plain") == "🎉 1. Done"


@pytest.mark.parametrize("text", [c for c, _ in CASES] + ["Привет ✅ 🎉 мир", "🎉 1. Done"])
def test_idempotent(text):
    once = format_for_speech(text, profile="plain")
    assert format_for_speech(once, profile="plain") == once


@pytest.mark.parametrize("text,plain_out,markdown_out", [
    ("**✅ Done**", "(done) Done", "**(done) Done**"),
    ("**🎉 Hello**", "Hello", "**Hello**"),
    ("**Done** ✅", "Done (done)", "**Done** (done)"),
    ("**Done**✅", "Done (done)", "**Done** (done)"),
    ("Done ✅**x**", "Done (done) x", "Done (done) **x**"),
])
def test_emoji_next_to_emphasis_keeps_delimiters_tight(text, plain_out, markdown_out):
    assert format_for_speech(text, profile="plain") == plain_out
    assert format_for_speech(text, profile="markdown") == markdown_out


@pytest.mark.parametrize("text,expected", [
    ("✅ ◽ ready ◾", "(done) ready"),
    ("✅ Ⓜ️ Metro", "(done) Metro"),
    (f"👨{ZWJ}⚕️ doctor ❤{ZWJ}🔥 ok ❤️ love", "doctor ok love"),
    ("⚠ bare warning ✔ bare", "(warning) bare warning (done) bare"),
])
def test_more_emoji_presentations(text, expected):
    assert format_for_speech(text, profile="plain") == expected


@pytest.mark.parametrize("text", [
    "Play F♯ and B♭, not F and B.",
    "Rated ★★★ ✓ approved, ♞ to f3, 🜁 air",
    "Arrows ⬅ and ↔ in text, © 2026 and ™",
    "Heart ❤ in text",
])
def test_text_symbols_are_kept(text):
    assert format_for_speech(text, profile="plain") is text
