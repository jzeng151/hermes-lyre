"""Quoted heading boundaries and isolated tildes in strike contents."""

import pytest

from lyre.formatter import format_for_speech


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("setext", [False, True])
@pytest.mark.parametrize("ticks", ["`", "``"])
def test_quoted_final_heading_keeps_code_span_boundary(profile, verbosity, setext, ticks):
    body = "text " + ticks
    heading = "> " + body + "\n> ===" if setext else "> # " + body
    code = ticks + "**code**" + ticks
    text = heading + "\n" + code
    expected = text
    if profile == "plain":
        expected = body + ".\n\n" + code
        if verbosity == "full":
            expected = "Quote:\nHeading: " + body + ".\n\nEnd of quote.\n" + code
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == expected
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("body", ["Pin dependency to ~1.2", "Use a~b~c", "~1.2", "version~"])
def test_strikethrough_allows_isolated_content_tildes(profile, verbosity, body):
    text = "~~" + body + "~~"
    # A content tilde touching a delimiter makes a longer run, not an exact pair.
    expected = text if body.startswith("~") or body.endswith("~") else f"(removed: {body})"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == expected
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("width", [3, 4, 5, 6])
def test_strikethrough_does_not_cross_long_content_runs(profile, verbosity, width):
    text = "~~alpha " + "~" * width + " beta~~"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
