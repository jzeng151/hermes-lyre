"""Core pipeline tests (task T1): pass-through, span protection, the guard, quote containers."""

from __future__ import annotations

import time

import pytest

from lyre.formatter import format_for_speech
from lyre.formatter import rules
from lyre.formatter.core import is_latin

FIXTURES = {
    "prose": "The tests passed. Two files changed.",
    "table": "| Name | Price |\n|------|------:|\n| Alpha | $10 |\n| Beta | |",
    "list": "- Build\n- Test\n  - unit\n  - live\n- Ship\n\n1. one\n2) two",
    "headings": "# Title\n\nText\n\nSetext\n======\n\nSub\n---",
    "quote": "> quoted **text**\n> > nested\n>\n> - item",
    "fenced": "Intro\n\n```python\nprint(\"✅ **done**\")\n```\n\n~~~\nx | y\n~~~",
    "unclosed": "Before\n```js\nconst a = '**';\n\nstill code",
    "indented": "Para\n\n    x = 1\n    print(x)\n\nAfter",
    "indented_in_list": "- Example:\n\n      print(\"✅ **x**\")\n\n- next",
    "math": "Energy:\n\n$$\n\\text{**literal**} ✅\n$$\n\nand $$a^2$$ inline",
    "html": "<details><summary>More</summary>\n**inside**\n</details> <br/>",
    "escapes": "\\*literal\\* and \\# not a heading and \\| pipe",
    "urls": "See https://example.test/a_b?c=1&d=%20, or [docs](https://x.test/(a)/b \"t\").",
    "crlf": "Line one\r\n\r\n- item\r\n",
    "rtl": "مرحبا **بالعالم** ✅",
    "zwj": "👩🏽‍💻 Family 👨‍👩‍👧‍👦 1️⃣ 🏳️‍🌈",
    "surrogate": "bad \ud800 surrogate",
    "rules_and_boxes": "Top\n\n---\n\n┌──┐\n│ok│\n└──┘\n\n⠓⠑⠇⠇⠕",
    "code_span": "Run `npm test` or ``a ` b`` then \\`not code`.",
    "trailing_newline": "Ends with newline\n",
}

ALL_OPTIONS = [dict(profile=p, verbosity=v) for p in ("plain", "markdown") for v in ("brief", "normal", "full")]


@pytest.fixture
def temp_rules():
    """Register throwaway rules for one test and always remove them."""
    added: list[str] = []

    def add_inline(name, fn, order=100):
        rules.register_inline_rule(name, fn, order)
        added.append(name)

    def add_block(kind, fn):
        rules.register_block_rule(kind, fn)
        added.append(kind)

    yield add_inline, add_block
    for name in added:
        rules.unregister(name)


@pytest.mark.parametrize("name", sorted(FIXTURES))
@pytest.mark.parametrize("opts", ALL_OPTIONS, ids=lambda o: f"{o['profile']}-{o['verbosity']}")
def test_no_rules_means_identity(name, opts):
    text = FIXTURES[name]
    assert format_for_speech(text, **opts) is text


@pytest.mark.parametrize("text", ["", "   \n\t", "\n"])
def test_empty_input_returned(text):
    assert format_for_speech(text, profile="plain") is text


def test_oversize_input_is_the_same_object_and_fast():
    text = "**x** " * 40_000  # 240,000 bytes
    start = time.perf_counter()
    assert format_for_speech(text, profile="plain") is text
    assert time.perf_counter() - start < 0.005


@pytest.mark.parametrize("char", ["\ue000", "\ue001"])
def test_placeholder_characters_in_input_are_left_alone(temp_rules, char):
    add_inline, _ = temp_rules
    add_inline("upper", lambda t, o: t.upper())
    text = f"hello {char} world"
    assert format_for_speech(text, profile="plain") is text


def test_mixed_line_endings_left_alone(temp_rules):
    add_inline, _ = temp_rules
    add_inline("upper", lambda t, o: t.upper())
    text = "one\r\ntwo\nthree"
    assert format_for_speech(text, profile="plain") is text


def test_crlf_preserved_when_changed(temp_rules):
    add_inline, _ = temp_rules
    add_inline("upper", lambda t, o: t.upper())
    assert format_for_speech("one\r\ntwo\r\n", profile="plain") == "ONE\r\nTWO\r\n"


@pytest.mark.parametrize("bad", [dict(profile="loud"), dict(profile="plain", verbosity="max"),
                                 dict(profile="plain", emoji_policy="x"), dict(profile="plain", table_style="grid")])
def test_invalid_options_raise_value_error(bad):
    with pytest.raises(ValueError, match="must be one of"):
        format_for_speech("text", **bad)


def test_raising_rule_returns_input(temp_rules):
    add_inline, _ = temp_rules

    def boom(text, opts):
        raise RuntimeError("rule bug")

    add_inline("boom", boom)
    text = "**bold** text"
    assert format_for_speech(text, profile="plain") is text


def test_rule_returning_newline_returns_input(temp_rules):
    add_inline, _ = temp_rules
    add_inline("split", lambda t, o: t.replace(" ", "\n"))
    text = "two words"
    assert format_for_speech(text, profile="plain") is text


def test_empty_result_returns_input(temp_rules):
    add_inline, _ = temp_rules
    add_inline("erase", lambda t, o: "")
    text = "🎉"
    assert format_for_speech(text, profile="plain") is text


def test_inline_rules_never_see_protected_spans(temp_rules):
    add_inline, _ = temp_rules
    seen: list[str] = []
    add_inline("spy", lambda t, o: (seen.append(t), t.replace("*", ""))[1])
    text = FIXTURES["fenced"] + "\n\n" + FIXTURES["math"] + "\n\n" + FIXTURES["escapes"] + "\n\n" + FIXTURES["urls"]
    out = format_for_speech(text, profile="plain")
    joined = "\n".join(seen)
    for literal in ("print(", "\\text", "a_b?c=1", "x.test/(a)/b", "\\*literal\\*"):
        assert literal not in joined
    assert 'print("✅ **done**")' in out and "\\text{**literal**}" in out and "\\*literal\\*" in out


def test_indented_code_inside_list_item_is_protected(temp_rules):
    add_inline, _ = temp_rules
    add_inline("strip", lambda t, o: t.replace("*", ""))
    out = format_for_speech(FIXTURES["indented_in_list"] + " **x**", profile="plain")
    assert '      print("✅ **x**")' in out


def test_code_inside_quote_is_protected(temp_rules):
    add_inline, _ = temp_rules
    add_inline("strip", lambda t, o: t.replace("*", ""))
    text = '> intro **a**\n>\n>     print("✅ **done**")\n>\n> ```py\n> x = "**y**"\n> ```'
    out = format_for_speech(text, profile="plain")
    assert '>     print("✅ **done**")' in out
    assert '> x = "**y**"' in out
    assert "> intro a" in out


def test_quote_recursion_depth_cap(temp_rules):
    add_inline, _ = temp_rules
    add_inline("strip", lambda t, o: t.replace("*", ""))
    deep = ">" * 12 + " **deep**"
    assert format_for_speech(deep, profile="plain") == deep
    shallow = "> > **two**"
    assert format_for_speech(shallow, profile="plain") == "> > two"


@pytest.mark.parametrize("line", ["[- Build](https://x.test)", "🎉 1. Done", "**# Title**", "** - x**", "**|a|**"])
def test_guard_restores_exposed_block_syntax(temp_rules, line):
    add_inline, _ = temp_rules
    add_inline("strip", lambda t, o: t.replace("**", "").replace("🎉 ", "").replace("[", "").replace("](", " (")
               if t.startswith(("[", "🎉", "**")) else t)
    text = f"Before\n\n{line}\n\nAfter"
    assert format_for_speech(text, profile="plain") is text


def test_guard_catches_setext_underline(temp_rules):
    add_inline, _ = temp_rules
    add_inline("strip", lambda t, o: t.replace("**", ""))
    text = "Title\n**===**"
    assert format_for_speech(text, profile="plain") is text


def test_guard_restores_block_rule_output(temp_rules):
    _, add_block = temp_rules
    add_block("heading", lambda b, o, inline: [b.lines[0].lstrip("# ") + "."])
    assert format_for_speech("# - Build", profile="plain") == "# - Build"
    assert format_for_speech("# Results", profile="plain") == "Results."


def test_removed_block_collapses_blank_lines(temp_rules):
    _, add_block = temp_rules
    add_block("rule", lambda b, o, inline: [])
    assert format_for_speech("A\n\n---\n\nB", profile="plain") == "A\n\nB"
    assert format_for_speech("---\n\nB", profile="plain") == "B"


def test_unchanged_spacing_kept_but_changed_lines_trimmed(temp_rules):
    add_inline, _ = temp_rules
    add_inline("strip", lambda t, o: t.replace("**", ""))
    assert format_for_speech("keep  two  spaces\n**x** ", profile="plain") == "keep  two  spaces\nx"


@pytest.mark.parametrize("sample,expected", [
    ("Hello world, this is English.", True),
    ("こんにちは、世界。これは日本語です。", False),
    ("مرحبا بالعالم هذا نص عربي", False),
    ("Привет мир, это русский текст", False),
    ("Café déjà vu, naïve façade", True),
    ("12345 !!!", True),
])
def test_script_detection(sample, expected):
    assert is_latin([sample]) is expected


def test_options_reach_rules(temp_rules):
    add_inline, _ = temp_rules
    seen = []
    add_inline("spy", lambda t, o: (seen.append(o), t)[1])
    format_for_speech("Привет мир", profile="markdown", verbosity="full", emoji_policy="keep", table_style="unchanged")
    opts = seen[0]
    assert (opts.profile, opts.verbosity, opts.emoji_policy, opts.table_style, opts.latin) == (
        "markdown", "full", "keep", "unchanged", False)


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_idempotent_with_a_rule(temp_rules, name):
    add_inline, _ = temp_rules
    add_inline("strip", lambda t, o: t.replace("**", ""))
    once = format_for_speech(FIXTURES[name], profile="plain")
    assert format_for_speech(once, profile="plain") == once


def test_registry_rejects_duplicates(temp_rules):
    add_inline, add_block = temp_rules
    add_inline("dup", lambda t, o: t)
    add_block("table", lambda b, o, i: None)
    with pytest.raises(ValueError):
        rules.register_inline_rule("dup", lambda t, o: t)
    with pytest.raises(ValueError):
        rules.register_block_rule("table", lambda b, o, i: None)
