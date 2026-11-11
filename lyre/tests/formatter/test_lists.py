"""R5 lists (task T5)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

NESTED = "- Build\n- Test\n  - unit\n  - live\n- Ship"


def plain(text: str, **kw) -> str:
    return format_for_speech(text, profile="plain", **kw)


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
    assert out == "2 items.\n1, Example:\n\n      print(\"✅ **x**\")\n\n2, next"


def test_fence_opened_on_item_line():
    out = plain("- ```py\n  x='**'\n  ```\n- after")
    assert out == "2 items.\n1,\n```py\n  x='**'\n  ```\n2, after"


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
    assert once.count("code") == 0  # no code labels yet (R7), and none added on the second pass


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
     'Example:\n\n    - ```py\n    x = "**bold**"\n    - ```\n\nAfter bold'),
    # block syntax inside an item: the list is left to default handling
    ("- a\n  ---\n- b", "- a\n  ---\n- b"),
    # an item emptied by the inline rules keeps only its number
    ("- 🎉\n- b", "2 items.\n1,\n2, b"),
    # a change of marker type starts a separate list
    ("- Prerequisite\n\n1. Build\n2. Test", "1 item.\n1, Prerequisite\n\n2 items.\n1, Build\n2, Test"),
    # a link labelled x is not a task box
    ("- [x](https://example.com)\n- Other", "2 items.\n1, [x](https://example.com)\n2, Other"),
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
    ("-     ```py\n- **next**\n\nAfter **bold**", "-     ```py\n1 item.\n1, next\n\nAfter bold"),
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
