"""Strikethrough and heading boundary regressions."""

import pytest

from lyre.formatter import format_for_speech


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("width", [3, 4, 5, 6])
def test_long_strikethrough_runs_are_not_partially_rewritten(profile, verbosity, width):
    marker = "~" * width
    text = f"Text {marker}gone{marker}"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("target", ["https://example.com", "https://example.com/a_**b**?x=1&y=2"])
@pytest.mark.parametrize("setext", [False, True])
def test_link_targets_do_not_block_heading_rewrite(profile, verbosity, target, setext):
    body = f"**See** [docs]({target})"
    text = body + "\n===" if setext else "# " + body
    spoken = f"docs, link: {target}"
    expected = text.replace(f"[docs]({target})", spoken)
    if profile == "plain":
        expected = f"See {spoken}."
        if verbosity == "full":
            expected = "Heading: " + expected
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == expected
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("setext", [False, True])
@pytest.mark.parametrize("ticks", ["`", "``"])
def test_rewritten_heading_keeps_code_span_boundary(profile, verbosity, setext, ticks):
    body = "text " + ticks
    heading = body + "\n===" if setext else "# " + body
    code = ticks + "**code**" + ticks
    text = heading + "\n" + code
    expected = text
    if profile == "plain":
        expected = body + ".\n\n" + code
        if verbosity == "full":
            expected = "Heading: " + expected
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == expected
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
