"""Container boundaries and source-sensitive guard regressions."""

import pytest

from lyre.formatter import blocks, core, rules


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(rules, "_block_rules", {})
    monkeypatch.setattr(rules, "_inline_rules", [])


@pytest.mark.parametrize("marker", ["-   ", "123. ", "-\t"])
def test_list_blank_requires_actual_content_column(marker):
    text = marker + "item\n\n  outside prose"
    seen = []
    rules.register_block_rule("list", lambda block, opts, inline: seen.append(block.lines))
    assert core.format_for_speech(text, profile="plain") == text
    assert seen == [[marker + "item"]]
    assert [block.kind for block in blocks.segment(text.split("\n"))] == ["list", "blank", "paragraph"]


@pytest.mark.parametrize("marker, indent", [("- ", "  "), ("1. ", "   "), ("-   ", "    ")])
def test_list_blank_can_resume_parent_after_nested_child(marker, indent):
    text = (f"{marker}Parent\n{indent}- child\n\n{indent}Parent continuation\n"
            f"{indent}- second child\n- Next")
    seen = []
    rules.register_block_rule("list", lambda block, opts, inline: seen.append(block.lines))
    assert core.format_for_speech(text, profile="plain") == text
    assert seen == [text.split("\n")]
    segmented = blocks.segment(text.split("\n"))
    assert [block.kind for block in segmented] == ["list"]
    assert segmented[0].lines == text.split("\n")


@pytest.mark.parametrize("quote", [
    "> Привет мир\nэто длинный русский текст",
    "> Привет `English code`\nэто русский текст https://english.example/test",
])
def test_preserved_lazy_quote_still_contributes_prose_script(quote):
    seen = []
    rules.register_inline_rule("spy", lambda text, opts: (seen.append(opts.latin), text)[1])
    text = quote + "\n\n✅"
    assert core.format_for_speech(text, profile="plain") == text
    assert seen and not any(seen)
    assert core._reply_letter_counts(quote)[0] == 0


def test_deep_quote_scanning_has_linear_slice_work():
    class TrackedLine(str):
        sliced = 0

        def __getitem__(self, key):
            value = super().__getitem__(key)
            if isinstance(key, slice):
                type(self).sliced += len(value)
                return type(self)(value)
            return value

        def removeprefix(self, prefix):
            return self[len(prefix):] if self.startswith(prefix) else self

    line = TrackedLine("> " * 20_000 + "hello")
    assert blocks._quote_end([line], 0) == 1
    assert TrackedLine.sliced <= len(line) * 4
    assert core.format_for_speech(line, profile="plain") == line


def test_unwrapped_quote_code_keeps_paragraph_boundary():
    rules.register_block_rule("blockquote", lambda block, opts, inline: block.meta["inner_out"])
    rules.register_inline_rule("strip", lambda text, opts: text.replace("**", ""))
    text = "Intro\n>     **literal**"
    out = core.format_for_speech(text, profile="plain")
    assert out == "Intro\n\n    **literal**"
    assert core.format_for_speech(out, profile="plain") == out


def test_changed_line_count_cannot_borrow_other_lines_list_syntax():
    def rewrite(block, opts, inline):
        return ["count: 1", *(line.replace("**", "") for line in block.lines)]

    rules.register_block_rule("list", rewrite)
    text = "- item\n  **- literal**"
    assert core.format_for_speech(text, profile="plain") == text
    assert core.format_for_speech(text, profile="plain") == text


def test_changed_line_count_can_keep_unchanged_source_syntax():
    rules.register_block_rule("list", lambda block, opts, inline: ["count: 1", *block.lines]
                              if block.meta["prev_text"] != "count: 1" else None)
    text = "- item\n  plain"
    out = core.format_for_speech(text, profile="plain")
    assert out == "count: 1\n" + text
    assert core.format_for_speech(out, profile="plain") == out
