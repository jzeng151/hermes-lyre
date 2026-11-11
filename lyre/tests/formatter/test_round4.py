"""Protected-container precedence regressions."""

import pytest

from lyre.formatter import blocks, core, rules


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(rules, "_block_rules", {})
    monkeypatch.setattr(rules, "_inline_rules", [])


@pytest.mark.parametrize("target", ["/path/**literal**`x", "../**literal**`x", "<relative/**literal**`x>"])
def test_link_destination_backtick_cannot_open_prose_code(target):
    rules.register_inline_rule("strip", lambda text, opts: text.replace("**", ""))
    text = f"[a]({target}) and ` **prose**"
    out = core.format_for_speech(text, profile="plain")
    assert out == f"[a]({target}) and ` prose"
    assert core.format_for_speech(out, profile="plain") == out


@pytest.mark.parametrize("code", [
    "```python\n  > English words inside protected code only\n  > ```",
    "$$\n  > English words inside protected math only\n  > $$",
])
def test_list_nested_quote_counts_code_as_one_container(code):
    seen = []
    rules.register_inline_rule("spy", lambda text, opts: (seen.append(opts.latin), text.replace("**", ""))[1])
    text = f"- Пример\n  > {code}\n\nПривет мир ✅ **текст**"
    out = core.format_for_speech(text, profile="plain")
    assert seen and not any(seen)
    assert out == text.replace("**текст**", "текст")
    assert core._reply_letter_counts(text)[0] == 0
    assert core.format_for_speech(out, profile="plain") == out


@pytest.mark.parametrize("math", ["> $$\n> x\n> $$", "> $$x$$"])
def test_closed_quote_math_does_not_capture_outside_prose(math):
    rules.register_inline_rule("strip", lambda text, opts: text.replace("**", ""))
    text = math + "\n**outside**"
    out = core.format_for_speech(text, profile="plain")
    assert out == math + "\noutside"
    assert [block.kind for block in blocks.segment(text.split("\n"))] == ["blockquote", "paragraph"]
    assert core.format_for_speech(out, profile="plain") == out


def test_code_opened_before_link_shaped_text_keeps_precedence():
    rules.register_inline_rule("strip", lambda text, opts: text.replace("**", ""))
    text = "`[a](/path/**literal**`x) and **prose**"
    out = core.format_for_speech(text, profile="plain")
    assert out == "`[a](/path/**literal**`x) and prose"
    assert core.format_for_speech(out, profile="plain") == out
