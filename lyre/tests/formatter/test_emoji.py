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
    # A run mixing status and other emoji: status words in place, the rest kept as written.
    ("✅ 🎉 ⚠️ 🔴", "(done) 🎉 (warning) (red)"),
    ("✅🎉", "(done) 🎉"),
    ("🎉✅🎊", "🎉 (done) 🎊"),
    ("🎉🎊 ✅", "🎉🎊 (done)"),
    ("Build ✅🚀 shipped", "Build (done) 🚀 shipped"),
    # Emoji Lyre has no word for are kept byte for byte (ADR 0008).
    ("🎉 Hello", "🎉 Hello"),
    ("Hello 🎉 world", "Hello 🎉 world"),
    ("Hello 🎉🎊  world 🎉", "Hello 🎉🎊  world 🎉"),
    ("Done 🎉.", "Done 🎉."),
    ("Status ✅", "Status (done)"),
    (f"👩🏽{ZWJ}💻 Family 👨{ZWJ}👩{ZWJ}👧{ZWJ}👦 1️⃣ #️⃣ *️⃣ 🏳️{ZWJ}🌈",
     f"👩🏽{ZWJ}💻 Family 👨{ZWJ}👩{ZWJ}👧{ZWJ}👦 1️⃣ #️⃣ *️⃣ 🏳️{ZWJ}🌈"),
    ("👍🏽 Text ✨\ufe0e", "👍🏽 Text ✨\ufe0e"),
    (f"🙂{ZWJ}↔️ Hello 🙂{ZWJ}↕️", f"🙂{ZWJ}↔️ Hello 🙂{ZWJ}↕️"),
    ("🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f Hello",
     "🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f Hello"),
    ("🇯🇵 Tokyo", "🇯🇵 Tokyo"),
    ("  🎉 Indented  prose\n  🎉 Child", "  🎉 Indented  prose\n  🎉 Child"),
    ("* 🎉 First\n* ⚠️ Second", "2 items.\n1, 🎉 First\n2, (warning) Second"),
    ("Heading\n🎉\nNext", "Heading\n🎉\nNext"),
    ("2 * 3 ✅ ©️ © ↔ ↔️ ⭐ x", "2 * 3 (done) ©️ © ↔ ↔️ ⭐ x"),
    ("The answer is 🇫🇷, not 🇩🇪.", "The answer is 🇫🇷, not 🇩🇪."),
    ("Use key 1️⃣ to continue.", "Use key 1️⃣ to continue."),
    ("Rated ⭐⭐⭐⭐ out of 5", "Rated ⭐⭐⭐⭐ out of 5"),
    ("Temp 30°C ☀️ today", "Temp 30°C ☀️ today"),
    ("✅ 🏻 ready", "(done) 🏻 ready"),
]

REMOVE_CASES = [
    ("✅ 🎉 ⚠️ 🔴", ""),
    ("✅ 🎉 ⚠️ 🔴 now", "now"),
    ("🎉 Hello", "Hello"),
    ("Hello 🎉 world", "Hello world"),
    ("Hello 🎉🎊  world 🎉", "Hello world"),
    ("Done 🎉.", "Done."),
    (f"👩🏽{ZWJ}💻 Family 👨{ZWJ}👩{ZWJ}👧{ZWJ}👦 1️⃣ #️⃣ *️⃣ 🏳️{ZWJ}🌈", "Family"),
    ("👍🏽 Text ✨\ufe0e", "Text"),
    (f"🙂{ZWJ}↔️ Hello 🙂{ZWJ}↕️", "Hello"),
    ("🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f Hello", "Hello"),
    ("🇯🇵 Tokyo", "Tokyo"),
    ("  🎉 Indented  prose\n  🎉 Child", "  Indented  prose\n  Child"),
    ("* 🎉 First\n* ⚠️ Second", "2 items.\n1, First\n2, Second"),
    ("Heading\n🎉\nNext", "Heading\nNext"),
    ("2 * 3 ✅ ©️ © ↔ ↔️ ⭐ x", "2 * 3 © ↔ x"),
    ("The answer is 🇫🇷, not 🇩🇪.", "The answer is, not."),
    ("Rated ⭐⭐⭐⭐ out of 5", "Rated out of 5"),
]


@pytest.mark.parametrize("text,expected", CASES)
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_words_policy(text, expected, profile):
    if profile == "markdown" and "*" in text:
        pytest.skip("markdown profile keeps list markers and emphasis; covered elsewhere")
    assert format_for_speech(text, profile=profile) == expected


@pytest.mark.parametrize("text,expected", REMOVE_CASES)
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_remove_policy(text, expected, profile):
    if profile == "markdown" and "*" in text:
        pytest.skip("markdown profile keeps list markers and emphasis; covered elsewhere")
    once = format_for_speech(text, profile=profile, emoji_policy="remove")
    assert once == (expected or text)  # an emoji-only reply falls back to the input
    assert format_for_speech(once, profile=profile, emoji_policy="remove") == once


@pytest.mark.parametrize("text,expected", [
    ("# 🚀 Deploy\nRun it.", "🚀 Deploy.\nRun it."),
    ("## ✅ Done\nAll good.", "(done) Done.\nAll good."),
])
def test_decorative_heading_emoji_is_kept(text, expected):
    assert format_for_speech(text, profile="plain") == expected


@pytest.mark.parametrize("text", [
    "`✅ code` and ```🎉```",
    "https://example.test/🎉/a_✅?x=1",
    "```\nprint('✅ 🎉')\n```",
    "plain text, no emoji",
])
def test_protected_and_emoji_free_text_untouched(text):
    assert text in format_for_speech(text, profile="plain")  # code may gain R7 labels


def test_emoji_only_reply_falls_back_to_input():
    assert format_for_speech("🎉 🎊", profile="plain") == "🎉 🎊"


def test_link_label_keeps_url_emoji():
    out = format_for_speech("🎉 [details](https://example.test/a_✅?x=1)", profile="plain")
    assert out == "🎉 details, link: https://example.test/a_✅?x=1"
    out = format_for_speech("🎉 [details](https://example.test/a_✅?x=1)", profile="plain",
                            emoji_policy="remove")
    assert out == "details, link: https://example.test/a_✅?x=1"


def test_remove_policy_drops_status_emoji_too():
    assert format_for_speech("✅ done 🎉 now", profile="plain", emoji_policy="remove") == "done now"


def test_keep_policy_skips_the_rule():
    text = "✅ done 🎉"
    assert format_for_speech(text, profile="plain", emoji_policy="keep") is text


def test_non_latin_reply_keeps_every_emoji():
    assert format_for_speech("Привет ✅ 🎉 мир", profile="plain") == "Привет ✅ 🎉 мир"
    assert format_for_speech("Привет ✅ 🎉 мир", profile="plain", emoji_policy="remove") == "Привет мир"


@pytest.mark.parametrize("policy", ["words", "remove"])
def test_exposed_list_marker_after_removal_is_guarded(policy):
    assert format_for_speech("🎉 1. Done", profile="plain", emoji_policy=policy) == "🎉 1. Done"


@pytest.mark.parametrize("text", [c for c, _ in CASES] + ["Привет ✅ 🎉 мир", "🎉 1. Done"])
def test_idempotent(text):
    once = format_for_speech(text, profile="plain")
    assert format_for_speech(once, profile="plain") == once


@pytest.mark.parametrize("text,plain_out,markdown_out", [
    ("**✅ Done**", "(done) Done", "**(done) Done**"),
    ("**🎉 Hello**", "🎉 Hello", "**🎉 Hello**"),
    ("**Done** ✅", "Done (done)", "**Done** (done)"),
    ("**Done**✅", "Done (done)", "**Done** (done)"),
    ("Done ✅**x**", "Done (done) x", "Done (done) **x**"),
])
def test_emoji_next_to_emphasis_keeps_delimiters_tight(text, plain_out, markdown_out):
    assert format_for_speech(text, profile="plain") == plain_out
    assert format_for_speech(text, profile="markdown") == markdown_out


@pytest.mark.parametrize("text,words,removed", [
    ("✅ ◽ ready ◾", "(done) ◽ ready ◾", "ready"),
    ("✅ Ⓜ️ Metro", "(done) Ⓜ️ Metro", "Metro"),
    (f"👨{ZWJ}⚕️ doctor ❤{ZWJ}🔥 ok ❤️ love", f"👨{ZWJ}⚕️ doctor ❤{ZWJ}🔥 ok ❤️ love", "doctor ok love"),
    ("⚠ bare warning ✔ bare", "(warning) bare warning (done) bare", "bare warning bare"),
])
def test_more_emoji_presentations(text, words, removed):
    assert format_for_speech(text, profile="plain") == words
    assert format_for_speech(text, profile="plain", emoji_policy="remove") == removed


@pytest.mark.parametrize("text", [
    "Play F♯ and B♭, not F and B.",
    "Rated ★★★ ✓ approved, ♞ to f3, 🜁 air",
    "Arrows ⬅ and ↔ in text, © 2026 and ™",
    "Heart ❤ in text",
])
def test_text_symbols_are_kept(text):
    assert format_for_speech(text, profile="plain") is text


@pytest.mark.parametrize("text", ["☝🏽 Next", "✌🏽 Next", "✍🏽 Next", "⛹🏽 Next"])
def test_text_default_base_with_skin_tone_is_one_unit(text):
    assert format_for_speech(text, profile="plain") == text  # kept whole, no orphan tone
    assert format_for_speech(text, profile="plain", emoji_policy="remove") == "Next"


def test_emoji_then_drawing_line_removed_in_one_pass():
    for profile in ("plain", "markdown"):
        out = format_for_speech("Intro\n🎉 ───\nEnd", profile=profile, emoji_policy="remove")
        assert out == "Intro\nEnd"
        # Under words the emoji is kept, so the line is not drawing-only and stays.
        assert format_for_speech("Intro\n🎉 ───\nEnd", profile=profile) == "Intro\n🎉 ───\nEnd"


def test_emoji_letter_does_not_count_as_script():
    once = format_for_speech("ℹ️ ✅", profile="plain")
    assert once == "ℹ️ (done)"
    assert format_for_speech(once, profile="plain") == once


@pytest.mark.parametrize("text,plain_out,markdown_out", [
    ("(**✅ Done**)", "((done) Done)", "(**(done) Done**)"),
    ("**Done 🎉**.", "Done 🎉.", "**Done 🎉**."),
])
def test_emphasis_delimiters_beside_punctuation(text, plain_out, markdown_out):
    assert format_for_speech(text, profile="plain") == plain_out
    assert format_for_speech(text, profile="markdown") == markdown_out


def test_removed_emoji_beside_closing_delimiter_and_punctuation():
    assert format_for_speech("**Done 🎉**.", profile="plain", emoji_policy="remove") == "Done."
    assert format_for_speech("**Done 🎉**.", profile="markdown", emoji_policy="remove") == "**Done**."


@pytest.mark.parametrize("text,expected", [
    ("Cross 🕆 symbol", "Cross 🕆 symbol"),       # not an emoji at all
    ("Use 🖥 and 🛠 here", "Use 🖥 and 🛠 here"),   # text by default, no selector
    ("Use 🖥️ and 🛠️ here", "Use and here"),        # emoji with the selector
])
def test_supplementary_text_symbols(text, expected):
    assert format_for_speech(text, profile="plain", emoji_policy="remove") == expected
    assert format_for_speech(text, profile="plain") == text  # words keeps them all


@pytest.mark.parametrize("text,kw,expected", [
    ("Hello **🎉** world", {"emoji_policy": "remove"}, "Hello world"),
    ("Hello **✅** world", {"emoji_policy": "remove"}, "Hello world"),
    ("Hello *🎉*.", {"emoji_policy": "remove"}, "Hello."),
    ("un*🎉*able", {"emoji_policy": "remove"}, "un able"),
    ("un**✅**able", {"emoji_policy": "remove"}, "un able"),
    ("Hello **✅** world", {}, "Hello (done) world"),
])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_emptied_emphasis_wrapper_is_removed(text, kw, expected, profile):
    out = format_for_speech(text, profile=profile, **kw)
    if profile == "markdown" and "(done)" in expected:
        expected = "Hello **(done)** world"
    assert out == expected
    assert format_for_speech(out, profile=profile, **kw) == out


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["remove"])
@pytest.mark.parametrize("marks", ["*", "**", "***"])
def test_delimiters_of_neighbouring_spans_are_kept(profile, policy, marks):
    text = f"*one*🎉{marks}two{marks}"
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == ("one two" if profile == "plain" else f"*one* {marks}two{marks}")
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("text,plain_out,markdown_out", [
    ("un*🎉believ*able", "unbelievable", "un*believ*able"),
    ("*Hello🎉*world", "Helloworld", "*Hello*world"),
    ("*🎉Hello🎊*world", "Helloworld", "*Hello*world"),
    ("un**🎉believ**able", "unbelievable", "un**believ**able"),
    ("un***🎉believ***able", "unbelievable", "un***believ***able"),
    ("这是*🎉强调*文字", "这是强调文字", "这是*强调*文字"),
])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["words", "remove", "keep"])
def test_emoji_preserves_intraword_asterisk_emphasis(text, plain_out, markdown_out, profile, policy):
    if policy in ("keep", "words"):  # no status emoji: words keeps every emoji, like keep
        expected = text.replace("*", "") if profile == "plain" else text
    else:
        expected = plain_out if profile == "plain" else markdown_out
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == expected
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("text,plain_out,markdown_out", [
    ("un*✅believ*able", "un(done) believable", "un*(done) believ*able"),
    ("*Hello✅*world", "Hello (done)world", "*Hello (done)*world"),
])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_status_words_preserve_intraword_asterisk_emphasis(text, plain_out, markdown_out, profile):
    expected = plain_out if profile == "plain" else markdown_out
    out = format_for_speech(text, profile=profile)
    assert out == expected
    assert format_for_speech(out, profile=profile) == out


@pytest.mark.parametrize("text,expected", [
    ("un_🎉believ_able", "un_ believ_able"),
    ("_Hello🎉_world", "_Hello _world"),
    ("un__🎉believ__able", "un__ believ__able"),
    ("2*🎉3*4", "2* 3*4"),
    ("2*3🎉*4", "2*3 *4"),
])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["words", "remove", "keep"])
def test_emoji_does_not_reinterpret_literal_intraword_markers(text, expected, profile, policy):
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == (text if policy in ("keep", "words") else expected)
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["words", "remove", "keep"])
@pytest.mark.parametrize("text,removed,kept", [
    ("Use ~~old🎉~~new instead", "Use (removed: old)new instead",
     "Use (removed: old🎉)new instead"),
    ("Use old~~🎉bad~~ instead", "Use old(removed: bad) instead",
     "Use old(removed: 🎉bad) instead"),
    ("Use old~~🎉bad🎊~~new instead", "Use old(removed: bad)new instead",
     "Use old(removed: 🎉bad🎊)new instead"),
    ("Use old~~🎉~~new instead", "Use old new instead",
     "Use old(removed: 🎉)new instead"),
])
def test_emoji_preserves_intraword_strikethrough(profile, policy, text, removed, kept):
    expected = kept if policy in ("keep", "words") else removed
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == expected
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["remove"])
@pytest.mark.parametrize("text,plain_out,markdown_out", [
    ("*🎉hello🎊*world", "helloworld", "*hello*world"),
    ("old*🎉*new *🎊hi*end", "old new hiend", "old new *hi*end"),
    ("*🎉* *🎊hi*end", "hiend", "*hi*end"),
])
def test_original_pairing_survives_multiple_run_edits(text, plain_out, markdown_out, profile, policy):
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == (plain_out if profile == "plain" else markdown_out)
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["remove"])
def test_run_between_word_and_emptied_wrapper_keeps_word_boundary(profile, policy):
    text = "hi🎉**🎉**there"
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == "hi there"
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["remove"])
@pytest.mark.parametrize("text,plain_out,markdown_out", [
    ("**one🎉**🎊 two", "one two", "**one** two"),
    ("**one🎉**🎊two", "one two", "**one** two"),
    ("one 🎉**🎊two**", "one two", "one **two**"),
])
def test_run_delimiters_use_original_line_context(text, plain_out, markdown_out, profile, policy):
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == (plain_out if profile == "plain" else markdown_out)
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["words", "remove", "keep"])
@pytest.mark.parametrize("text,plain_out,markdown_out", [
    ("**🎉*important* details**", "important details", "***important* details**"),
    ("**details *important*🎉**", "details important", "**details *important***"),
    ("*🎉**important** details*", "important details", "***important** details*"),
    ("*details **important**🎉*", "details important", "*details **important***"),
])
def test_removed_emoji_between_nested_delimiters(text, plain_out, markdown_out, profile, policy):
    if policy in ("keep", "words"):  # no status emoji: words keeps every emoji, like keep
        expected = text.replace("*", "") if profile == "plain" else text
    else:
        expected = plain_out if profile == "plain" else markdown_out
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == expected
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("tone", [chr(cp) for cp in range(0x1F3FB, 0x1F400)])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy", ["words", "remove", "keep"])
def test_standalone_skin_tones_follow_emoji_policy(tone, profile, policy):
    text = f"✅ {tone} ready"
    expected = {"keep": text, "words": f"(done) {tone} ready", "remove": "ready"}[policy]
    out = format_for_speech(text, profile=profile, emoji_policy=policy)
    assert out == expected
    assert format_for_speech(out, profile=profile, emoji_policy=policy) == out


@pytest.mark.parametrize("text", ["\u0628\u062d*\u26a0 x*", "\u0628\u062d\u26a0 \u0631", "\u65e5\u672c\u2705\u8a9e",
                                  "\u65e5\u672c\u8a9e\u2705 **\u26a0**"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_kept_emoji_spacing_is_left_alone(text, profile):
    # Found by the fuzz tests: a gap decided next to a ``*`` that emphasis later removed.
    once = format_for_speech(text, profile=profile)
    assert format_for_speech(once, profile=profile) == once


# Inputs from the delimiter and spacing fixes above, found by fuzzing. They hold no status emoji,
# so under words the emoji rule leaves them alone and the output matches the keep policy.
NO_STATUS_INPUTS = [
    "*one*🎉**two**", "Hello **🎉** world", "Hello *🎉*.", "un*🎉*able", "un*🎉believ*able",
    "*🎉Hello🎊*world", "这是*🎉强调*文字", "un_🎉believ_able", "2*🎉3*4", "Use old~~🎉~~new instead",
    "*🎉* *🎊hi*end", "hi🎉**🎉**there", "**one🎉**🎊 two", "one 🎉**🎊two**", "**🎉*important* details**",
    "[🎉](https://example.test/a) and [✨]: /path", "<b🎉text>", "Intro\n🎉 ───\nEnd",
]


@pytest.mark.parametrize("text", NO_STATUS_INPUTS)
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_words_without_status_emoji_matches_keep(text, profile):
    out = format_for_speech(text, profile=profile)
    assert out == format_for_speech(text, profile=profile, emoji_policy="keep")
    assert format_for_speech(out, profile=profile) == out
