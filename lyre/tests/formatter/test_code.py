"""R7 code blocks (task T7; fences kept on every profile, spec Q1)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

SPEC = '```python\nprint("✅ **done**")\n```'


def plain(text: str, **kw) -> str:
    return format_for_speech(text, profile="plain", **kw)


def test_spec_example():
    assert plain(SPEC) == 'Python code, 1 line:\n```python\nprint("✅ **done**")\n```\nEnd of code.'


def test_brief_and_full():
    assert plain(SPEC, verbosity="brief") == 'Code:\n```python\nprint("✅ **done**")\n```\nEnd of code.'
    assert plain(SPEC, verbosity="full") == plain(SPEC)


@pytest.mark.parametrize("info,name", [("js", "JavaScript"), ("TS", "TypeScript"), ("c++", "C++"), ("sh", "Shell"),
                                       ("diff", "Diff"), ("python title=x.py", "Python"), ("", "Code"),
                                       ("brainfuck", "Code")])
def test_language_names(info, name):
    label = name if name == "Code" else f"{name} code"
    assert plain(f"```{info}\na\nb\n```").startswith(f"{label}, 2 lines:\n")


def test_tilde_fence_and_contents_byte_identical():
    body = "select 1;  \n\n\t-- **x** ✅"
    out = plain(f"~~~sql\n{body}\n~~~")
    assert out == f"SQL code, 3 lines:\n~~~sql\n{body}\n~~~\nEnd of code."


def test_unclosed_fence_unchanged():
    text = "Intro\n```py\nx = '**y**'\nstill code"
    assert plain(text) == text


def test_markdown_profile_also_labels():
    assert format_for_speech(SPEC, profile="markdown").startswith("Python code, 1 line:")


def test_non_latin_reply_gets_no_labels():
    text = "Вот пример кода для вас, пожалуйста\n\n```py\nx = 1\n```"
    assert plain(text) == text


def test_ac21_indented_code_labelled_once_and_byte_identical():
    text = "Para\n\n    x = 1  \n    print(x)\n\nAfter"
    once = plain(text)
    assert once == "Para\n\nCode, 2 lines:\n\n    x = 1  \n    print(x)\n\nEnd of code.\n\nAfter"
    assert plain(once) == once


def test_ac21_indented_code_inside_list_item():
    text = "- Example:\n\n      print(\"✅ **x**\")\n\n- next"
    once = plain(text)
    assert "      print(\"✅ **x**\")" in once
    assert once.count("Code, 1 line:") == 1
    assert plain(once) == once


def test_fence_on_list_item_line_is_labelled():
    assert plain("- ```py\n  x='**'\n  ```\n- after") == (
        "2 items.\n1,\nPython code, 1 line:\n```py\n  x='**'\n  ```\nEnd of code.\n2, after")


def test_ac23_code_inside_quote():
    for profile in ("plain", "markdown"):
        once = format_for_speech("> ```py\n> x = '**y**'\n> ```", profile=profile)
        assert "x = '**y**'" in once
        assert format_for_speech(once, profile=profile) == once


CASES = [SPEC, "Intro\n```js\na()\nb()\n```\nAfter", "Para\n\n    x = 1\n\nAfter", "```\nunclosed",
         "- Example:\n\n      x = 1\n\n- n", "- ```py\n  x='**'\n  ```\n- after", "> ```py\n> x = 1\n> ```",
         "- a\n  - b\n    - c:\n\n      ```py\n      s = '✅ **x**'\n      ```\n    - d"]


@pytest.mark.parametrize("text", CASES)
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_idempotent(text, verbosity, profile):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


def test_math_in_list_item_is_not_labelled_as_code():
    out = format_for_speech("- Math:\n  $$x^2$$\n- next", profile="plain")
    assert "code" not in out.lower()
    assert "  $$x^2$$" in out.split("\n")


def test_many_code_blocks_in_one_item_stay_fast():
    import time
    text = "- item\n" + "".join(f"\n  ```\n  x{i}\n  ```\n" for i in range(3000))
    start = time.perf_counter()
    once = format_for_speech(text, profile="plain")
    assert time.perf_counter() - start < 2.0
    assert format_for_speech(once, profile="plain") == once


def test_label_on_the_item_line_is_recognized():
    text = "- Python code, 1 line:\n  ```py\n  x\n  ```\n  End of code."
    once = format_for_speech(text, profile="plain")
    assert once.count("Python code, 1 line:") == 1 and once.count("End of code.") == 1
    assert format_for_speech(once, profile="plain") == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_removed_first_line_does_not_expose_code(profile):
    once = format_for_speech("🎉\n    print('x')", profile=profile)
    assert "code" not in once.lower()
    assert format_for_speech(once, profile=profile) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_decoration_before_fence_stays_separate_from_code_label(profile, verbosity):
    code = "```py\nx  \n```"
    once = format_for_speech("🎉\n" + code, profile=profile, verbosity=verbosity)
    assert code in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
