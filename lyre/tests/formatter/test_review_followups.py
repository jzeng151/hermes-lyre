"""Regression tests for the review findings and fuzz inputs deferred to #43.

Each case is the reproduction from its review thread (or the shrunk fuzz input), formatted
twice: the second pass must equal the first, and protected bytes must survive.
"""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

from . import fuzzgen


def twice(text: str, **kw) -> str:
    once = format_for_speech(text, **kw)
    assert format_for_speech(once, **kw) == once
    return once


# Core span protection (#33).
def test_math_on_a_list_marker_line_is_protected():
    assert "\\text{**literal**}" in twice("- $$\n  \\text{**literal**}\n  $$\n\n**prose**", profile="plain")


def test_inline_math_never_reaches_into_a_link_destination():
    out = twice("[a](/path/**literal**$$x) and $$ **prose**", profile="plain")
    assert "/path/**literal**$$x" in out and "**prose**" not in out


def test_backtick_inside_inline_math_is_literal():
    out = twice("before $$**literal** `$$ and ` **prose**", profile="plain")
    assert "$$**literal** `$$" in out


@pytest.mark.parametrize("text", [">\t**quoted prose**\n\n**outside**", "> >\t**nested**"])
def test_tab_after_quote_marker_is_prose(text):
    assert "**" not in twice(text, profile="plain")


def test_spaced_break_does_not_open_a_list():
    assert "    **literal**" in twice("* * *\n\n    **literal**\n\n**prose**", profile="plain").split("\n")


# Emphasis, quotes and headings (#34).
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_nested_strikethrough_resolves_in_one_pass(profile):
    assert twice("~~a ~~b~~ c~~", profile=profile) == "(removed: a (removed: b) c)"


def test_quoted_setext_line_stays_text_at_full_verbosity():
    out = twice("> ===", profile="plain", verbosity="full")
    assert "Heading" not in out and "===" in out


@pytest.mark.parametrize("text,expected", [("**Edit *.py files**", "Edit *.py files"),
                                           ("__snake_case__", "snake_case")])
def test_strong_emphasis_holds_a_literal_single_marker(text, expected):
    assert twice(text, profile="plain") == expected


# Emoji (#35).
@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("policy,expected", [("words", "(done) ready"), ("remove", "ready")])
def test_lone_regional_indicator_is_an_emoji(profile, policy, expected):
    assert twice("\u2705 \U0001F1E6 ready", profile=profile, emoji_policy=policy) == expected


# Lists (#36, #38).
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_ordered_marker_not_starting_at_one_is_not_a_child(profile):
    assert "sub-item" not in twice("- a\n  2. not a child\n- c", profile=profile)


def test_list_after_kept_quote_gets_one_label_pair():
    out = twice("> text\n- item\n  ```py\n  x\n  ```", profile="markdown")
    assert out.count("Python code, 1 line:") == 1 and out.count("End of code.") == 1


# Fuzz inputs, shrunk to their smallest failing form.
@pytest.mark.parametrize("text,profile", [
    ("`\U0001F44D`*`*", "plain"),                                     # markers beside an unmatched backtick
    ("\u062d<b\u2728\u0628\u0628>ax\u26a0\u65e5", "plain"),           # an emoji gap that would form a tag
    ("[\u2728]:\U0001F680", "markdown"),                              # an emoji that is a whole label
])
def test_shrunk_fuzz_inputs_are_idempotent(text, profile):
    twice(text, profile=profile)


@pytest.mark.parametrize("seed,profile", [(544, "plain"), (955, "plain"), (1485, "plain"), (1485, "markdown"),
                                          (1588, "plain"), (1588, "markdown"), (1911, "plain")])
def test_reported_fuzz_seeds_are_idempotent(seed, profile):
    twice(fuzzgen.soup(seed), profile=profile)


# Second review round on the follow-ups.
def test_unclosed_strong_with_many_single_pairs_is_linear():
    import time
    start = time.perf_counter()
    format_for_speech("**" + "a*b*" * 200 + "z", profile="plain")
    assert time.perf_counter() - start < 0.5
    assert twice("**a *b* c**", profile="plain") == "a b c"


def test_math_starting_in_a_destination_does_not_hide_code():
    assert "`**code**`" in twice("[a](/p$$x) `**code**` $$ **prose**", profile="plain")


def test_tabs_inside_quoted_code_are_kept():
    out = twice(">\t```text\n>\t>\tvalue\n>\t```", profile="plain")
    assert ">\tvalue" in out


def test_break_inside_an_item_keeps_the_list():
    out = twice("- parent\n  * * *\n\n    **continuation prose**", profile="plain")
    assert "**continuation prose**" not in out


# Third review round on the follow-ups.
def test_math_and_link_overlap_check_is_not_quadratic():
    import time
    text = "[a](b) " * 10000 + "$$x$$ " * 10000
    start = time.perf_counter()
    format_for_speech(text, profile="plain")
    assert time.perf_counter() - start < 2.0


def test_indented_line_after_a_break_is_code():
    out = twice("* * *\n    ```\n**prose**\n\n- item", profile="plain")
    assert "**prose**" not in out and "1, item" in out


@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_ordered_child_after_item_code_is_spoken(profile):
    out = twice("- ```py\n  x\n  ```\n  2. child", profile=profile)
    assert "Python code" in out and "child" in out


def test_over_indented_break_shape_is_paragraph_text():
    out = twice("paragraph\n    ---\n    **continuation prose**", profile="plain")
    assert "Code" not in out and "**continuation prose**" not in out
