"""Titled links stay as written; tight inline math is protected (ADR 0009, spec step 2 and R8)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

PROFILES = ["plain", "markdown"]


def fmt(text: str, profile: str = "plain") -> str:
    return format_for_speech(text, profile=profile)


TITLED = [
    '[policy](https://example.test "Do not share externally")',
    "[policy](https://example.test 'Do not share')",
    "[policy](https://example.test (Do not share))",
    '[policy](<https://example.test/a b> "Title")',
    '![chart](https://example.test/c.png "Sales by month")',
    '[**bold** label](https://example.test "Title")',
    '[policy](/relative/path "Title")',
    '[![chart](https://x.test/c.png "Chart")](https://x.test/page)',
    '[![chart](https://x.test/c.png)](https://x.test/page "Page")',
]


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("text", TITLED)
def test_titled_link_is_left_as_written(text, profile):
    assert fmt(text, profile) == text
    assert fmt(f"See {text} now.", profile) == f"See {text} now."


@pytest.mark.parametrize("profile", PROFILES)
def test_titled_link_title_survives_in_a_list_and_emphasis_around_it_is_still_removed(profile):
    text = '- **Read** [policy](https://example.test "Do not share externally")'
    out = fmt(text, profile)
    assert '[policy](https://example.test "Do not share externally")' in out
    if profile == "plain":
        assert "**" not in out
    assert fmt(out, profile) == out


def test_titled_link_title_on_next_line_is_kept():
    text = 'See [policy](https://example.test\n"Do not share externally") now.'
    out = fmt(text)
    assert '"Do not share externally"' in out
    assert fmt(out) == out


@pytest.mark.parametrize("profile", PROFILES)
def test_untitled_links_keep_current_behavior(profile):
    assert fmt("[docs](https://x.test/a?b=1)", profile) == "docs, link: https://x.test/a?b=1"
    assert fmt("![chart](https://x.test/c.png)", profile) == "Image: chart, link: https://x.test/c.png"
    assert fmt("[docs](<https://x.test>)", profile) == "docs, link: https://x.test"


MATH = [
    "$a*b*c$",
    "$x_1 + x_2 = *y*$",
    "\\(a*b*c\\)",
    "\\[a*b*c\\]",
    "$a$",
    "Inline $E = m*c^2*$ and \\(a_b_c\\) together.",
    "$\\$5 *x*$",
]


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("text", MATH)
def test_inline_math_is_left_as_written(text, profile):
    assert fmt(text, profile) == text
    assert fmt(fmt(text, profile), profile) == fmt(text, profile)


@pytest.mark.parametrize("text,expected", [
    ("Price is $5 and *really* $10.", "Price is $5 and really $10."),
    ("$5-$10 is *fine*", "$5-$10 is fine"),
    ("costs $3.50, about $4 *each*", "costs $3.50, about $4 each"),
    ("from $5 to $10 *total*", "from $5 to $10 total"),
    ("$ a*b*c $ is *not* math", "$ abc $ is not math"),
    ("costs $5/$10 *each*", "costs $5/$10 each"),
])
def test_currency_is_not_math(text, expected):
    out = fmt(text)
    assert out == expected
    assert fmt(out) == out


def test_escaped_dollars_are_not_math():
    text = "\\$a *b* c\\$"
    out = fmt(text)
    assert "*" not in out
    assert fmt(out) == out


def test_escaped_paren_opener_is_not_math():
    # An escaped backslash before ``(`` is a literal backslash, not a math opener.
    out = fmt("\\\\(a *b* c\\\\)")
    assert "*" not in out


@pytest.mark.parametrize("profile", PROFILES)
def test_display_math_still_protected(profile):
    for text in ("$$a*b*c$$", "Inline $$a*b*c$$ display.", "$$\na*b*c\n$$"):
        assert fmt(text, profile) == text


@pytest.mark.parametrize("profile", PROFILES)
def test_math_inside_code_span_stays_code(profile):
    for text in ("`$a*b*c$`", "`\\(a*b*c\\)`", "Run `echo $HOME*$USER` now"):
        assert fmt(text, profile) == text


def test_math_never_reaches_into_a_link_destination():
    text = "[x](https://e.test/$a*b*$) $y*z*w$"
    assert fmt(text) == "x, link: https://e.test/$a*b*$ $y*z*w$"
    text = "$a [x](https://e.test/b$c) *d*"
    out = fmt(text)
    assert "https://e.test/b$c" in out
    assert "*d*" not in out
    assert fmt(out) == out


def test_math_never_starts_inside_a_bare_url():
    text = "see https://e.test/$a*b*$ and *c*"
    out = fmt(text)
    assert "https://e.test/$a*b*$" in out
    assert "*c*" not in out


def test_paren_math_needs_one_line():
    out = fmt("\\(a *b*\nc\\)")
    assert "*b*" not in out


def test_unclosed_paren_math_is_linear():
    import time
    text = "\\(a " * 5000 + "*b*"
    start = time.perf_counter()
    out = fmt(text)
    assert time.perf_counter() - start < 1.0
    assert "*b*" not in out


@pytest.mark.parametrize("cell", ['[p](https://x.test "t")', "$a*b*$", r"\(a*b\)"])
def test_titled_link_and_math_in_a_table_cell_are_kept(cell):
    out = fmt(f"| A |\n|---|\n| {cell} |")
    assert out.startswith("Table, 1 row")
    assert cell in out
    assert fmt(out) == out


def test_label_with_nested_brackets_keeps_its_title():
    out = fmt('[a [b] **c**](https://x.test "t") z')
    assert '(https://x.test "t")' in out
    assert fmt(out) == out


def test_escaped_dollar_does_not_hide_the_math_after_it():
    # The escaped ``$`` is skipped and the search resumes on the next character, as a second
    # pass would after the emoji between them is removed.
    text = r"\$🚀$x*y*$"
    once = fmt(text)
    assert "$x*y*$" in once
    assert fmt(once) == once
