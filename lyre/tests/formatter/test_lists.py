"""R5 lists (task T5)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

NESTED = "- Build\n- Test\n  - unit\n  - live\n- Ship"


def plain(text: str, **kw) -> str:
    return format_for_speech(text, profile="plain", **kw)


@pytest.mark.parametrize("text", [
    "- a\n      - b\n- c",
    "- a\n       - b\n- c",
    "- parent\n  - a\n        - b\n- c",
    "10. a\n        - b\n11. c",
])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_overindented_marker_does_not_invent_child_list(text, verbosity, profile):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("ending", ["2. Not a new list.", "0) Not a new list.", "2.", "1.", "1)"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_ordered_marker_cannot_interrupt_paragraph(ending, verbosity, profile):
    text = "The answer is\n" + ending
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("text", [
    "- > ~~~python\n  > **literal**\n  > ~~~\n- next",
    "- parent\n  - > ~~~python\n    > **literal**\n    > ~~~\n- next",
    "1. > ~~~python\n   > **literal**\n   > ~~~\n2. next",
])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_item_start_quote_keeps_fenced_code_bytes(text, verbosity, profile):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("indent", [2, 3, 4, 5])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_nested_marker_within_three_extra_columns_is_a_list(indent, verbosity, profile):
    text = "- a\n" + " " * indent + "- b\n- c"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert "  sub-item 1, b" in once
    assert "2, c" in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("prefix,marker", [
    ("The answer is\n", "1."),
    ("The answer is\n", "1)"),
    ("The answer is\n\n", "2."),
    ("", "2."),
    ("# Heading\n", "2."),
])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_valid_ordered_list_start_is_still_spoken(prefix, marker, verbosity, profile):
    text = prefix + marker + " Item"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert marker[:-1] + ", Item" in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


def test_spec_example_normal():
    assert plain(NESTED) == ("3 items.\n1, Build\n2, Test\n  2 sub-items.\n  sub-item 1, unit\n"
                             "  sub-item 2, live\n3, Ship")


def test_brief_has_no_count_lines():
    assert plain(NESTED, verbosity="brief") == "1, Build\n2, Test\n  sub-item 1, unit\n  sub-item 2, live\n3, Ship"


def test_full_names_lists_and_ends_them():
    assert plain(NESTED, verbosity="full") == (
        "List, 3 items.\n1, Build\n2, Test\n  Sub-list, 2 items.\n  sub-item 1, unit\n  sub-item 2, live\n"
        "3, Ship\nEnd of list.")


@pytest.mark.parametrize("text,expected", [
    ("5. Five\n6. Six", "2 items.\n5, Five\n6, Six"),
    ("1) x\n2) y", "2 items.\n1, x\n2, y"),
    ("- only", "1 item.\n1, only"),
    ("- [x] Done\n- [ ] Open", "2 items.\n1, (done) Done\n2, (not done) Open"),
    ("* one\n\n* two", "2 items.\n1, one\n\n2, two"),
    ("- **bold** item\n  continued *line*\n- 🎉 party", "2 items.\n1, bold item\ncontinued line\n2, party"),
    ("- run `npm **test**`", "1 item.\n1, run `npm **test**`"),
])
def test_items(text, expected):
    assert plain(text) == expected


def test_markdown_profile_also_speaks_lists_but_keeps_emphasis():
    assert format_for_speech("- **a**\n- b", profile="markdown") == "2 items.\n1, **a**\n2, b"


def test_deep_levels_are_spoken_and_indented_two_spaces():
    out = plain("- a\n  - b\n    - c\n    - d\n      - e")
    assert out == ("1 item.\n1, a\n  1 sub-item.\n  sub-item 1, b\n  2 level 3 items.\n  level 3 item 1, c\n"
                   "  level 3 item 2, d\n  1 level 4 item.\n  level 4 item 1, e")


def test_non_latin_list_gets_numbers_only():
    assert plain("- Привет\n  - мир") == "1, Привет\n  1, мир"


def test_indented_code_in_item_keeps_bytes():
    out = plain("- Example:\n\n      print(\"✅ **x**\")\n\n- next")
    assert out == "2 items.\n1, Example:\n\nCode, 1 line:\n\n      print(\"✅ **x**\")\n\nEnd of code.\n\n2, next"


def test_fence_opened_on_item_line():
    out = plain("- ```py\n  x='**'\n  ```\n- after")
    assert out == "2 items.\n1,\nPython code, 1 line:\n```py\n  x='**'\n  ```\nEnd of code.\n2, after"


def test_ac18_three_levels_with_fence_in_deepest_item():
    text = "- a\n  - b\n    - c:\n\n      ```py\n      s = '✅ **x**'\n      ```\n    - d"
    once = plain(text)
    twice = plain(once)
    assert twice == once
    assert "      s = '✅ **x**'" in once
    fence = False
    for line in once.split("\n"):
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            assert len(line) - len(line.lstrip(" ")) < 4, line
    assert once.count("Python code, 1 line:") == once.count("End of code.") == 1  # one R7 label pair


CASES = [NESTED, "5. Five\n6. Six", "- [x] Done", "- a\n  - b\n    - c\n      - d", "- Example:\n\n      x = 1\n\n- n",
         "- ```py\n  x='**'\n  ```\n- after", "Intro:\n- a\n- b\nAfter", "- Привет\n  - мир"]


@pytest.mark.parametrize("text", CASES)
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_idempotent(text, verbosity, profile):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("text,expected", [
    # indented code that starts with a marker and a fence stays code
    ('Example:\n\n    - ```py\n    x = "**bold**"\n    - ```\n\nAfter **bold**',
     'Example:\n\nCode, 3 lines:\n\n    - ```py\n    x = "**bold**"\n    - ```\n\nEnd of code.\n\nAfter bold'),
    # block syntax inside an item: the list is left to default handling
    ("- a\n  ---\n- b", "- a\n  ---\n- b"),
    # an item emptied by the inline rules keeps only its number
    ("- 🎉\n- b", "2 items.\n1,\n2, b"),
    # a change of marker type starts a separate list
    ("- Prerequisite\n\n1. Build\n2. Test", "1 item.\n1, Prerequisite\n\n2 items.\n1, Build\n2, Test"),
    # a link labelled x is not a task box
    ("- [x](https://example.com)\n- Other", "2 items.\n1, x, link: https://example.com\n2, Other"),
    # prose after a nested list returns to its owning item and ends the nested list
    ("- Parent\n  - child\n\n  Parent continuation\n  - second child\n- Next",
     "2 items.\n1, Parent\n  1 sub-item.\n  sub-item 1, child\n\nParent continuation\n"
     "  1 sub-item.\n  sub-item 1, second child\n2, Next"),
])
def test_review_round_structure(text, expected):
    once = plain(text)
    assert once == expected
    assert plain(once) == once


@pytest.mark.parametrize("text,expected", [
    # inline rules exposing a list marker on a continuation line: the line is kept as written
    ("- a\n  🎉 - hidden\n- b", "2 items.\n1, a\n🎉 - hidden\n2, b"),
    # a marker short of the content column is a sibling, not a child
    ("- first\n - second\n- third", "3 items.\n1, first\n2, second\n3, third"),
    # an item fence with no closing line inside its item: the list stays as written
    ("- ```py\n  code\n- **next**\n\nAfter **bold**", "- ```py\n  code\n- next\n\nAfter bold"),
    # five spaces after the marker: indented code, not an item fence
    ("-     ```py\n- **next**\n\nAfter **bold**",
     "Code, 1 line:\n\n-     ```py\n\nEnd of code.\n1 item.\n1, next\n\nAfter bold"),
])
def test_review_round_four_lists(text, expected):
    once = plain(text)
    assert once == expected
    assert plain(once) == once


def test_tab_after_marker_counts_as_columns():
    once = plain("-\tfirst\n  - second\n- third")
    assert once == "3 items.\n1, first\n2, second\n3, third"
    assert plain(once) == once


def test_outdented_sibling_stays_in_nested_list():
    once = plain("- parent\n   - first child\n  - second child\n- next")
    assert once == "2 items.\n1, parent\n  2 sub-items.\n  sub-item 1, first child\n  sub-item 2, second child\n2, next"
    assert plain(once) == once


def test_outdented_top_level_sibling_stays_in_the_list():
    once = plain(" - first\n- second")
    assert once == "2 items.\n1, first\n2, second"
    assert plain(once) == once


def test_unclosed_continuation_fence_keeps_the_list():
    text = "- a\n  ```py\n  code\n- **b**\n\nAfter **bold**"
    once = plain(text)
    assert once == "- a\n  ```py\n  code\n- b\n\nAfter bold"
    assert plain(once) == once


@pytest.mark.parametrize("text,expected", [
    # a four-backtick fence closed by three is still open: the list stays as written
    ("- ````py\n  x\n  ```\n- **b**\n\nAfter **bold**", "- ````py\n  x\n  ```\n- b\n\nAfter bold"),
    # a nested thematic break that looks like an item: left as written
    ("- a\n  * * *\n- b", "- a\n  * * *\n- b"),
    # a sibling at another indent with a new marker type starts a new list
    ("- Prerequisite\n\n 1. Build\n 2. Test", "1 item.\n1, Prerequisite\n\n2 items.\n1, Build\n2, Test"),
    # a list nested on its parent's marker line: left as written
    ("- - first child\n  - second child\n- next", "- - first child\n  - second child\n- next"),
])
def test_review_round_six_lists(text, expected):
    once = plain(text)
    assert once == expected
    assert plain(once) == once


@pytest.mark.parametrize("text", [
    "10. ```py\n    code\n    ```\n11. next",
    "- parent\n  - ```py\n    code\n    ```\n- next",
])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_item_fence_with_invalid_standalone_closer_keeps_markers(text, verbosity, profile):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert text.split("\n")[0] in once
    assert "    code\n    ```" in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_list_boundary_blank_preserves_following_indented_code(verbosity, profile):
    text = "100. a\n     - b\n\n  para\n\n    **code**"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert "\n\n    **code**" in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("literal", ["**literal**", "~~literal~~"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_unmatched_backtick_keeps_list_inline_boundaries(literal, verbosity, profile):
    text = f"- unmatched `\n- `{literal}`"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert f"`{literal}`" in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("text", [
    "- a\n  ===\n- b",
    "- parent\n  - child\n    ===\n- next",
    "1. heading\n   continuation\n   =\n2. next",
])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_nested_setext_heading_keeps_list_container(text, verbosity, profile):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("text", [
    "- [id]: https://example.com\n- See [id]",
    "- parent\n  - [id]: /destination\n  - See [id]",
    '- [id]:\n    https://example.com\n    "A title"\n- See [id]',
    "- definitions:\n\n  [id]: https://example.com\n- See [id]",
])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_reference_definition_keeps_list_container(text, verbosity, profile):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("text", [
    "- a\n-\n  **===**\n- b",
    "- a | b\n  **---|---**\n- c",
    "- a\n  🎉 |\n  **---|---**\n- b",
    "- a | b\n  🎉\n  ---|---\n- c",
])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_continuation_emission_preserves_block_context(text, verbosity, profile):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    if "**" in text:
        assert text.splitlines()[-2].strip() in once
    else:
        # Keeping the separator cannot help when an emptied line exposes a table header.
        assert once.startswith("- a | b\n")
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("text", [
    "- a | b\n  🎉\n  ---|---\n- c",
    "- parent\n  - a | b\n    🎉\n    ---|---\n- c",
])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_list_rule_declines_unsafe_original_continuation(text, verbosity, profile):
    from lyre.formatter.core import _inline_fn
    from lyre.formatter.model import Block, Options
    from lyre.formatter.rules.lists import lists

    opts = Options(profile=profile, verbosity=verbosity)
    assert lists(Block("list", text.splitlines()), opts, _inline_fn(opts)) is None
