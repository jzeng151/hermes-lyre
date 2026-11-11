"""Deterministic work bounds for formatter fast paths, not wall-clock limits."""

import sys

import pytest

from lyre.formatter import blocks, core, spans
from lyre.formatter.spans import Stash


def test_ascii_letter_counts_avoid_python_character_classification():
    calls = []

    def tracked(frame, event, arg):
        if event == "c_call" and getattr(arg, "__name__", None) == "isalpha":
            calls.append(arg)

    previous = sys.getprofile()
    try:
        sys.setprofile(tracked)
        counts = core._letter_counts(["Abc xyz 123 !", "\ue000i0\ue001"])
    finally:
        sys.setprofile(previous)
    assert counts == (6, 6)
    assert calls == []


@pytest.mark.parametrize(("text", "expected"), [
    ("Az 123!", (2, 2)), ("éЖ中文", (1, 4)), ("ℹ️abc", (3, 3)),
    ("\ue000i123\ue001Ж", (0, 1)), ("123 !", (0, 0)),
])
def test_letter_fast_path_preserves_script_counts(text, expected):
    assert core._letter_counts([text]) == expected


@pytest.mark.parametrize(("before", "after", "expected_calls"), [
    (["same", "old"], ["same", "new"], [("new", "same")]),
    (["old"], ["new", "plain"], [("new", None), ("plain", "new")]),
    (["", "==="], ["title", "==="], [("title", None), ("===", "title"), ("===", "")]),
])
def test_guard_only_classifies_needed_lines(monkeypatch, before, after, expected_calls):
    original = core.syntax_categories
    calls = []

    def tracked(line, prev):
        calls.append((line, prev))
        return original(line, prev)

    monkeypatch.setattr(core, "syntax_categories", tracked)
    assert core._guard(before, after, per_line=True) == after
    assert calls == expected_calls


@pytest.mark.parametrize(("before", "after", "expected"), [
    (["", "=== "], ["title", "==="], ["title", "=== "]),
    (["plain", "---"], ["a|b", "---"], ["a|b", "---"]),
    (["plain"], ["title", "==="], ["plain"]),
    (["plain", "text"], ["# new", "text"], ["plain", "text"]),
    (["plain", "text"], ["a|b", ":---|---:"], ["a|b", "text"]),
])
def test_guard_shortcuts_preserve_neighbor_context(before, after, expected):
    assert core._guard(before, after, per_line=True) == expected


@pytest.mark.parametrize("lines", [[], ["Ordinary prose", "", "- item", "# heading"]])
def test_marker_free_runs_skip_code_grouping(monkeypatch, lines):
    def unexpected(*args):
        pytest.fail("marker-free prose must not run grouping or span scanning")

    monkeypatch.setattr(spans, "_protect_code_spans", unexpected)
    assert spans.protect_code_spans(lines, Stash(), unexpected, unexpected, unexpected) == lines


@pytest.mark.parametrize("text", [
    "start `code\nend` tail",
    "[label](\n/destination)",
    "[id]:\n/destination",
    '<span title="one\ntwo">text',
])
def test_multiline_marker_filter_preserves_every_protected_kind(text):
    stash = Stash()
    result = spans.protect_code_spans(text.split("\n"), stash, lambda line: False)
    assert stash.values
    assert "\n".join(part for line in result for part in stash.restore(line)) == text


@pytest.mark.parametrize(("probe", "expected"), [
    (spans.is_block_token_line, False), (spans.block_token_kind, None),
])
def test_token_free_lines_skip_block_token_pattern(monkeypatch, probe, expected):
    class NoMatch:
        def match(self, line):
            pytest.fail("token-free prose must not run block token pattern")

    monkeypatch.setattr(spans, "BLOCK_TOKEN_RE", NoMatch())
    assert probe("  Ordinary prose") is expected


@pytest.mark.parametrize(("line", "expected"), [
    (" \t\ue000f12\ue001 ", "code"),
    ("\ue000c0\ue001", "code"),
    ("\ue000m3\ue001", "math"),
    ("\ue000i3\ue001", None),
    ("prefix \ue000f0\ue001", None),
    ("\ue000f0", None),
])
def test_block_token_filter_preserves_exact_match(line, expected):
    assert spans.block_token_kind(line) == expected
    assert spans.is_block_token_line(line) is (expected is not None)


def test_plain_thematic_break_skips_indentation(monkeypatch):
    def unexpected(line):
        pytest.fail("ordinary prose must not measure thematic indentation")

    monkeypatch.setattr(blocks, "indent_width", unexpected)
    assert not blocks.is_thematic_break("  Plain prose")


@pytest.mark.parametrize(("line", "expected"), [
    (" _ _ _ ", True), ("\t---", False), ("    ***", False), ("  - - -", True),
])
def test_thematic_filter_preserves_indentation(line, expected):
    assert blocks.is_thematic_break(line) is expected


def test_plain_syntax_skips_pattern_matching(monkeypatch):
    class NoMatch:
        def match(self, line):
            pytest.fail("ordinary prose must not run syntax patterns")

    monkeypatch.setattr(blocks, "LIST_ITEM_RE", NoMatch())
    assert blocks.syntax_categories("  Ordinary prose 123", "header | cell") == set()


@pytest.mark.parametrize(("line", "prev", "expected"), [
    ("_ _ _", None, {"rule"}),
    (":---|---:", "a|b", {"table"}),
    ("١. item", None, {"list"}),
    ("---", "heading", {"rule", "setext"}),
    ("\u2003|cell|", None, {"table"}),
    ("². not a decimal", None, set()),
])
def test_syntax_filter_preserves_nonobvious_starters(line, prev, expected):
    assert blocks.syntax_categories(line, prev) == expected


def test_marker_free_blocks_skip_all_inline_protection(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("marker-free blocks need no cell, span, or nested-quote protection")

    for name in ("protect_code_spans", "protect_inline", "protect_cells", "groupby"):
        monkeypatch.setattr(core, name, unexpected)
    text = "# Title\n\n**Build** passed\n\n| A | B |\n|---|---|\n| x | $10 |\n\n- one\n- two"
    assert core._protect(text, Stash()) == text.split("\n")


def test_unhandled_blocks_do_not_build_inline_pipeline(monkeypatch):
    def unexpected(*args):
        pytest.fail("blocks without a renderer or inline content need no inline pipeline")

    monkeypatch.setattr(core, "_inline_fn", unexpected)
    assert core._render(core.Block("blank", [""]), core.Options(profile="plain"), 0) is None


def test_plain_block_starters_skip_patterns(monkeypatch):
    class NoMatch:
        def match(self, line):
            pytest.fail("plain/table text cannot interrupt prose")

    monkeypatch.setattr(blocks, "QUOTE_RE", NoMatch())
    monkeypatch.setattr(blocks, "ATX_RE", NoMatch())
    monkeypatch.setattr(blocks, "LIST_ITEM_RE", NoMatch())
    assert not blocks.starts_block("  Ordinary prose")
    assert not blocks.starts_block("| a | b |")


def test_block_protection_skips_impossible_inputs(monkeypatch):
    def unexpected(*args):
        pytest.fail("no fences, math, indentation or wide item gaps: no block protection scan")

    monkeypatch.setattr(spans, "_code_threshold", unexpected)
    monkeypatch.setattr(spans, "_item_fence", unexpected)
    monkeypatch.setattr(spans, "_track_list", unexpected)
    lines = ["# Title", "", "**Build** passed", "|a|b|", "- one", "١. item", "[docs](url)"]
    assert spans.protect_blocks(lines, Stash()) == lines


def test_protected_block_kinds_skip_inline_protection(monkeypatch):
    def unexpected(*args):
        pytest.fail("blank, thematic and opaque blocks have no inline protection work")

    monkeypatch.setattr(core, "protect_code_spans", unexpected)
    monkeypatch.setattr(core, "protect_inline", unexpected)
    text = "\n \n***\n\n```py\nx = 1\n```\n\n$$x$$"
    stash = Stash()
    protected = core._protect(text, stash)
    assert "\n".join(part for line in protected for part in stash.restore(line)) == text


def test_render_reuses_protection_segmentation(monkeypatch):
    original = core.segment
    calls = []

    def tracked(lines):
        calls.append(lines)
        return original(lines)

    monkeypatch.setattr(core, "segment", tracked)
    text = "# Title\n\n**Build** passed\n\n| A | B |\n|---|---|\n| x | y |\n\n- one\n- two\n\n[docs](https://x.test)"
    errors = []
    out = core.format_for_speech(text, profile="plain", on_error=errors.append)
    assert "Title." in out and "Table, 1 row" in out and "docs" in out
    assert not errors
    assert len(calls) == 1


def test_ac8_payload_reuses_segmentation(monkeypatch):
    from lyre.tests.test_hook import REPLY, TABLE, callback

    original = core.segment
    calls = []

    def tracked(lines):
        calls.append(len(lines))
        return original(lines)

    monkeypatch.setattr(core, "segment", tracked)
    block = REPLY + "\n\n" + TABLE + "\n\n- one\n- two\n\n[docs](https://x.test/a?b=1)\n\n"
    text = (block * (20_000 // len(block) + 1))[:20_000]
    _, cb = callback(enabled=True)
    assert "Table, 1 row" in cb(response_text=text, platform="cli")
    assert len(calls) == 1


@pytest.mark.parametrize(("text", "reusable"), [
    ("# [Title](url)\n\n- [one](url)\n- two\n\nPlain `code`.", True),
    ("| `a|b` | c |\n|---|---|\n| [x](url) | y |", True),
    ("Plain \\*literal\\* and $$math$$.\nNext <b>line</b>.", True),
    ("start `code\nend` tail\n===\n\n**Other**", False),
    ("`a|b`\n---|---\nx|y", False),
    ("> lazy `code\ncontinuation`\n\n**tail**", False),
    ("> lazy words\ncontinuation\n\n**tail**", False),
    ("- item\n  > plain quote\n\n**tail**", False),
    ("- item\n\n  > quoted\n\n  continuation", False),
    ("- item\n  > ```\n  > code\n  > ```\n\nPlain.", False),
    ('<span title="one\ntwo">text\n\n- outside', False),
    ("[id]:\n/destination\n\n- outside", True),
])
def test_reused_segmentation_matches_fresh_protected_scan(text, reusable):
    stash = Stash()
    reused = []
    lines = core._protect(text, stash, reused)
    assert bool(reused) is reusable
    fresh = blocks.segment(lines)
    if reusable:
        assert reused == fresh
    assert "\n".join(part for line in lines for part in stash.restore(line)) == text


@pytest.mark.parametrize("text", [
    "```py\nx\n```", "~~~\nx\n~~~", "$$x$$", "\u2003$$x$$", "    code", "\tcode",
    "-     code", "١.     code", "-\t\tcode", "- ```py\n  x\n  ```",
    "- item\n\n      code",
])
def test_block_protection_prefilter_keeps_all_block_forms(text):
    stash = Stash()
    lines = spans.protect_blocks(text.split("\n"), stash)
    assert stash.values
    assert "\n".join(part for line in lines for part in stash.restore(line)) == text


@pytest.mark.parametrize("line", [
    "# heading", "> quote", "- item", "_ _ _", "***", "١. item", "  + item", "\t2) item",
    "\ue000f0\ue001", " \t\ue000m0\ue001",
])
def test_block_start_filter_preserves_supported_openers(line):
    assert blocks.starts_block(line)


def test_protection_segments_each_container_once(monkeypatch):
    original = core.segment
    calls = []

    def tracked(lines):
        calls.append(lines)
        return original(lines)

    monkeypatch.setattr(core, "segment", tracked)
    text = "- item\n  > nested `code`\n\n> lazy `code\ncontinuation`\n\nPlain prose."
    stash = Stash()
    protected = core._protect(text, stash)
    assert "\n".join(part for line in protected for part in stash.restore(line)) == text
    assert len(calls) == 1
