"""R8 inline code and links (task T8)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

SIGNED = ("https://bucket.s3.amazonaws.test/path/to/file_name__v2.tar.gz?X-Amz-Algorithm=AWS4-HMAC-SHA256"
          "&X-Amz-Credential=AKIA%2F20260101%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=ab_cd**ef__gh~~ij"
          "&response-content-disposition=attachment%3B%20filename%3D%22a_b_.zip%22")


def plain(text: str, **kw) -> str:
    return format_for_speech(text, profile="plain", **kw)


@pytest.mark.parametrize("text,expected", [
    ("`npm test`", "`npm test`"),
    ("[docs](https://x.test/a?b=1)", "docs, link: https://x.test/a?b=1"),
    ("[https://x.test](https://x.test)", "https://x.test"),
    ("<https://x.test>", "https://x.test"),
    ("![chart](https://x.test/c.png)", "Image: chart, link: https://x.test/c.png"),
    ("![](https://x.test/c.png)", "Image, link: https://x.test/c.png"),
    ("see https://x.test/a_b_c", "see https://x.test/a_b_c"),
    ('[**docs**](https://x.test/a_b "title")', "docs, link: https://x.test/a_b"),
    # a trailing underscore would fall outside the URL token on the next pass: link kept
    ('[**docs**](https://x.test/a_b_ "title")', '[docs](https://x.test/a_b_ "title")'),
    ("[`npm`](https://x.test)", "`npm`, link: https://x.test"),
    ("x ``a ` **b**`` y", "x ``a ` **b**`` y"),
])
def test_spec_table(text, expected):
    assert plain(text) == expected


@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_ac3_long_signed_url_byte_identical(profile):
    for text in (SIGNED, f"Download: {SIGNED}", f"[file]({SIGNED})"):
        out = format_for_speech(text, profile=profile)
        assert SIGNED in out
        assert format_for_speech(out, profile=profile) == out


def test_markdown_profile_rewrites_links_too():
    assert format_for_speech("[**docs**](https://x.test)", profile="markdown") == "**docs**, link: https://x.test"


def test_non_latin_reply_keeps_markdown_links():
    assert plain("Привет [док](https://x.test)") == "Привет [док](https://x.test)"


def test_inline_code_with_markup_stable_over_two_passes():
    text = "Run `x = '**y**' ✅` then `__init__.py`"
    assert plain(text) == text
    assert plain(plain(text)) == text


def test_ac22_label_that_starts_with_list_marker_is_not_exposed():
    text = "[- Build](https://x.test)"
    once = plain(text)
    assert not once.startswith("- ")
    assert plain(once) == once


CASES = ["[docs](https://x.test/a?b=1)", "<https://x.test/a_b>", "![chart](https://x.test/c.png)",
         "[https://x.test](https://x.test)", f"[file]({SIGNED})", "- [docs](https://x.test)",
         "| a |\n|---|\n| [x](https://y.test) |", "See [a](<https://x.test/a b>) now"]


@pytest.mark.parametrize("text", CASES)
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_idempotent(text, profile):
    once = format_for_speech(text, profile=profile)
    assert format_for_speech(once, profile=profile) == once


@pytest.mark.parametrize("text,expected", [
    ("[`a\nb`](https://x.test)\n\n**bold**", "`a\nb`, link: https://x.test\n\nbold"),
    ("[directory](./_private_)", "[directory](./_private_)"),
    ("[section](#_private_)", "[section](#_private_)"),
    ("[x](https://x.test/a.)", "[x](https://x.test/a.)"),
    ("[![Build status](https://ci.test/badge.svg)](https://ci.test/build)",
     "Image: Build status, source: https://ci.test/badge.svg, link: https://ci.test/build"),
    ("See [Foo](https://en.wikipedia.org/wiki/Foo_(bar)) now",
     "See Foo, link: https://en.wikipedia.org/wiki/Foo_(bar) now"),
])
@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_review_round_links(text, expected, profile):
    if profile == "markdown":
        expected = expected.replace("\n\nbold", "\n\n**bold**")
    once = format_for_speech(text, profile=profile)
    assert once == expected
    assert format_for_speech(once, profile=profile) == once


@pytest.mark.parametrize("text,expected", [
    ("[docs](https://x.test)suffix", "docs, link: https://x.test suffix"),
    ("[a](https://x.test)[b](https://y.test)", "a, link: https://x.test b, link: https://y.test"),
    ("[docs](https://x.test).", "docs, link: https://x.test."),
    ("[back]()\n\n**bold**", "[back]()\n\nbold"),
    ("[![](https://x.test/i.png)]()", "[![](https://x.test/i.png)]()"),
    ("[_docs_](https://x.test)", "docs, link: https://x.test"),
    ("[__docs__](https://x.test)", "docs, link: https://x.test"),
])
def test_review_round_two_links(text, expected):
    once = format_for_speech(text, profile="plain")
    assert once == expected
    assert format_for_speech(once, profile="plain") == once


def test_destination_holding_a_protected_span_stays():
    assert format_for_speech("[docs](<guide>)\n\n**bold**", profile="plain") == "[docs](<guide>)\n\nbold"


@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_autolink_followed_by_text_keeps_its_boundary(profile):
    out = format_for_speech("<https://x.test>suffix", profile=profile)
    assert out == "https://x.test suffix"
    assert format_for_speech(out, profile=profile) == out
