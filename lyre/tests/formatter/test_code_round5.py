"""Regression coverage for code label container boundaries."""

import pytest

from lyre.formatter import format_for_speech


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_label_does_not_join_lazy_quote(profile, verbosity):
    fence = "```py\nx\n```"
    once = format_for_speech("> text\n" + fence, profile=profile, verbosity=verbosity)
    assert fence in once
    assert once.count("End of code.") == 1
    for _ in range(3):
        assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("following", ["    y", "    prose follows"])
def test_label_does_not_expose_indented_continuation(profile, verbosity, following):
    text = "```py\nx\n```\n" + following
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert "```py\nx\n```" in once
    assert following in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_end_label_does_not_join_retained_setext_heading(profile, verbosity):
    text = "```py\nx\n```\n| a |\n==="
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    current = once
    for _ in range(3):
        current = format_for_speech(current, profile=profile, verbosity=verbosity)
        assert current == once
    assert once.count("End of code.") == 1
