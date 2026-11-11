"""R1 emphasis, R2 headings and R9 blockquotes (tasks T2)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech


def plain(text: str, **kw) -> str:
    return format_for_speech(text, profile="plain", **kw)


def md(text: str, **kw) -> str:
    return format_for_speech(text, profile="markdown", **kw)


@pytest.mark.parametrize("text,expected", [
    ("**bold** word", "bold word"),
    ("__bold__ word", "bold word"),
    ("*italic* word", "italic word"),
    ("_italic_ word", "italic word"),
    ("***both*** word", "both word"),
    ("~~gone~~ word", "(removed: gone) word"),
    ("**[docs](https://x.test/a_b_c)**", "[docs](https://x.test/a_b_c)"),
    ("- *item* one\n- __two__", "2 items.\n1, item one\n2, two"),
])
def test_emphasis_plain(text, expected):
    assert plain(text) == expected


@pytest.mark.parametrize("text", [
    "2 * 3 * 4",
    "snake_case_name and __init__.py",
    "\\*literal\\* and \\_x\\_",
    "`**code**` and `_x_`",
    "a ** b ** c",
    "url https://x.test/**a**/_b_",
])
def test_unpaired_escaped_and_protected_markers_kept(text):
    assert plain(text) is text


def test_markdown_profile_keeps_emphasis_but_converts_strikethrough():
    assert md("**bold** ~~gone~~") == "**bold** (removed: gone)"


def test_non_latin_reply_gets_no_inserted_words():
    assert plain("Привет ~~мир~~ **жирный**") == "Привет ~~мир~~ жирный"


@pytest.mark.parametrize("text,expected", [
    ("# Results", "Results."),
    ("## Done!", "Done!"),
    ("### Ready? ###", "Ready?"),
    ("Setext\n======", "Setext."),
    ("Sub\n---", "Sub."),
    ("# **Bold** title", "Bold title."),
    ("Intro\n# Results\nText", "Intro\n\nResults.\nText"),
    ("#", "#"),
])
def test_headings_plain(text, expected):
    assert plain(text) == expected


def test_heading_full_verbosity_names_level():
    assert plain("# Top\n\n### Deep", verbosity="full") == "Heading: Top.\n\nSubheading: Deep."


def test_heading_markdown_profile_untouched():
    text = "# Results\n\nSetext\n======"
    assert md(text) is text


def test_heading_that_would_expose_a_list_is_kept():
    assert plain("# - Build") == "# - Build"


def test_quote_markers_removed_on_plain():
    assert plain("> quoted **x**\n>\n> more") == "quoted x\n\nmore"


def test_multiline_setext_heading_keeps_every_line():
    assert plain("First line\nSecond line\n===") == "First line Second line."


@pytest.mark.parametrize("text,expected", [
    ("**bold *italic* text**", "bold italic text"),
    ("__bold _italic_ text__", "bold italic text"),
    ("*a **b** c*", "a b c"),
])
def test_nested_emphasis_resolves_in_one_pass(text, expected):
    assert plain(text) == expected


def test_quoted_indented_code_stays_code():
    once = plain("before\n>\n>     **code**")
    assert once == "before\n\n    **code**"
    assert plain(once) == once


def test_quoted_code_keeps_trailing_spaces():
    assert plain("> ```py\n> x = 1  \n> ```") == "```py\nx = 1  \n```"


def test_over_depth_quote_left_whole():
    text = "> " * 11 + "**x**"
    assert plain(text) == text


def test_non_latin_reply_with_quoted_english_code_gets_no_english():
    text = '> ```py\n> print("this is an English code example with many letters")\n> ```\n\n这是中文回复，~~删除~~。'
    for verbosity in ("normal", "full"):
        out = plain(text, verbosity=verbosity)
        assert "(removed:" not in out and "Quote:" not in out


def test_nested_quote_plain_and_full():
    assert plain("> a\n> > b") == "a\n\nb"
    assert plain("> a", verbosity="full") == "Quote:\na\nEnd of quote."


def test_quote_markdown_profile_keeps_markers_and_cleans_strikethrough():
    assert md("> ~~old~~ **new**") == "> (removed: old) **new**"


def test_quoted_code_survives_marker_removal():
    text = "> intro **a**\n>\n> ```py\n> x = '**y**'\n> ```"
    out = plain(text)
    assert out == "intro a\n\n```py\nx = '**y**'\n```"


CASES = [
    "**bold** _it_ ~~s~~", "Intro\n# Results\nText", "Setext\n======", "> q **x**\n> > n",
    "> ```py\n> x = '**y**'\n> ```", "# - Build", "Title\n**===**", "> # Quoted title",
    "First line\nSecond line\n===", "**bold *italic* text**", "before\n>\n>     **code**", "> " * 11 + "**x**",
]


@pytest.mark.parametrize("text", CASES)
@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_idempotent(text, profile, verbosity):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
