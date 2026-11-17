"""R10: prose backslash escapes that cannot become markup lose their backslash (#51)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

PROFILES = ("plain", "markdown")


def fmt(text: str, profile: str, **kw) -> str:
    return format_for_speech(text, profile=profile, **kw)  # type: ignore[arg-type]


def assert_stable(out: str, profile: str) -> None:
    assert fmt(out, profile) == out, "a second pass changed the output"


# Each removed escape: the bare character sits between words, with a space on both sides.
REMOVED = [
    ("2 \\* 3 = 6", "2 * 3 = 6"),
    ("a \\_ b", "a _ b"),
    ("2 \\* 3 = 6\n\n4 \\* 5 = 20", "2 * 3 = 6\n\n4 * 5 = 20"),
    ("2 \\* 3 = 6\nand 4 \\* 5 = 20", "2 * 3 = 6\nand 4 * 5 = 20"),
    ("2 \\* 3 and a \\_ b and c \\~ d", "2 * 3 and a _ b and c ~ d"),
    ("use x \\# 1", "use x # 1"),
    ("a \\- b \\+ c \\= d", "a - b + c = d"),
    ("a \\~ b", "a ~ b"),
    ("x \\> y and y \\< z", "x > y and y < z"),
    ("salt \\& pepper", "salt & pepper"),
    ("wow \\! yes", "wow ! yes"),
    ("a \\( b \\) c", "a ( b ) c"),
    ("a \\. b \\, c \\; d \\: e \\? f", "a . b , c ; d : e ? f"),
    ("a \\/ b \\% c \\@ d \\^ e", "a / b % c @ d ^ e"),
    ("a \\{ b \\} c", "a { b } c"),
    ("say \\\" hi \\' there", "say \" hi ' there"),
    ("x\t\\*\ty", "x\t*\ty"),
    ("日本 \\* 語", "日本 * 語"),
]


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("text,expected", REMOVED)
def test_spaced_escape_loses_backslash_and_is_stable(text, expected, profile):
    out = fmt(text, profile)
    assert out == expected
    assert_stable(out, profile)


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("text", [
    "- 2 \\* 3",
    "> 2 \\* 3 is six",
    "Text\n\n- one\n- 2 \\* 3",
    "> - a quoted item, 2 \\* 3",
])
def test_removed_inside_containers(text, profile):
    out = fmt(text, profile)
    assert "2 * 3" in out and "\\*" not in out
    assert_stable(out, profile)


def test_removed_in_heading_and_table():
    assert fmt("# Total 2 \\* 3", "markdown") == "# Total 2 * 3"
    assert fmt("# Total 2 \\* 3", "plain") == "Total 2 * 3."
    table = "| a | b |\n|---|---|\n| 2 \\* 3 | x |"
    for style in ("sentences", "unchanged"):
        for profile in PROFILES:
            out = fmt(table, profile, table_style=style)
            assert "2 * 3" in out and "\\*" not in out
            assert fmt(out, profile, table_style=style) == out


def test_removal_after_plain_emphasis_is_stable():
    # Plain removes the emphasis around the escape first; the escape is then the only asterisk.
    out = fmt("a*b \\* c*d", "plain")
    assert out == "ab * cd"
    assert_stable(out, "plain")
    # The markdown profile keeps the emphasis markers, so the escape keeps its backslash.
    assert fmt("a*b \\* c*d", "markdown") == "a*b \\* c*d"


# A client such as Telegram's adapter in Hermes v0.23.0 pairs any two asterisks on a line,
# escaped or not, flanking or not. An escape of *, _ or ~ loses its backslash only when it is
# the only one of that character on its line, counting code, URLs and other protected text.
@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("text", [
    "The total is 2 \\* 3 = 6, then a \\* b, x \\# 1 and \\_name\\_ with retry\\*limit.",
    "the total is 2 \\* 3 = 6, then 6 \\* 2",
    "2 \\* 3 \\* 4",
    "a \\_ b \\_ c",
    "a \\~ b \\~ c",
    "2 \\* 3 and retry\\*limit",
    "2 \\* 3 and 4 * 5",
    "a \\_ b and snake_case",
    "a \\~ b and ~~gone~~ c ~ d",
    "2 \\* 3 and `k*` in code",
    "2 \\* 3 at https://t.test/a*b now",
    "2 \\* 3 at [docs](https://t.test/a*b) now",
    "| 2 \\* 3 | 4 \\* 5 |\n|---|---|\n| a | b |",
])
def test_pairable_escape_kept_when_its_character_repeats_on_the_line(text, profile):
    out = fmt(text, profile, table_style="unchanged")
    assert "2 * 3" not in out and "a _ b" not in out and "a ~ b" not in out and "6 * 2" not in out
    assert fmt(out, profile, table_style="unchanged") == out


@pytest.mark.parametrize("profile", PROFILES)
def test_ci_reply_removes_only_the_unpairable_escape(profile):
    text = "The total is 2 \\* 3 = 6, then a \\* b, x \\# 1 and \\_name\\_ with retry\\*limit."
    out = fmt(text, profile)
    assert out == text.replace("x \\# 1", "x # 1")
    assert_stable(out, profile)


@pytest.mark.parametrize("profile", PROFILES)
def test_other_characters_do_not_need_to_be_unique(profile):
    out = fmt("a \\# b \\# c and 1 \\- 2 \\- 3", profile)
    assert out == "a # b # c and 1 - 2 - 3"
    assert_stable(out, profile)


# Each kept escape: removing it could change what the next pass (or the app) sees.
KEPT = [
    "retry\\*limit",                    # inside a word: could pair with another asterisk
    "\\_name\\_",                       # paired: would form emphasis
    "\\*literal\\* text",               # paired: would form emphasis
    "a \\| b",                          # pipe: could split a table row
    "\\# not heading",                  # line start: would become a heading
    "\\- not a list",                   # line start: would become a list item
    "1\\. not a list",                  # would become an ordered list
    "\\> not a quote",                  # line start: would become a quote
    "a \\[ b](c)",                      # bracket: would start a link
    "a \\] b",
    "a \\` b ` c",                      # backtick: would pair into code
    "a \\$ b $ c",                      # dollar: math in some apps
    "a \\\\ b",                         # an escaped backslash stays a backslash anyway
    "- \\* x",                          # after a list marker: would become a nested list
    "1. \\* x",
    "> \\* x",
    "2 \\*3",                           # no space after: could open emphasis
    "2\\* 3",                           # no space before: could close emphasis
    "2 \\* (3)",                        # not between two words
    "(2) \\* 3",
    "2 \\*\\* 3",                       # adjacent escapes: a run of two
    "line ends 2 \\*",                  # nothing after it
    "`code` \\* x",                     # next to a protected span, not a word
    "Telegram's adapter shows \\_name\\_ and retry\\*limit",
]


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("text", KEPT)
def test_unsafe_escape_kept(text, profile):
    out = fmt(text, profile)
    for line in text.split("\n"):
        for i, ch in enumerate(line):
            if ch == "\\" and i + 1 < len(line) and line[i + 1] in "*_|#-.>[]`$\\":
                assert line[i:i + 2] in out
    assert_stable(out, profile)


@pytest.mark.parametrize("profile", PROFILES)
def test_neighbouring_escapes_are_both_kept(profile):
    # Neither escape sits between two words: each has the other on one side.
    assert fmt("2 \\* \\* 3", profile) == "2 \\* \\* 3"


@pytest.mark.parametrize("profile", PROFILES)
def test_escaped_pipe_kept_in_unchanged_table(profile):
    table = "| a \\| b | c |\n|---|---|\n| 2 \\* 3 | x |"
    out = fmt(table, profile, table_style="unchanged")
    assert "a \\| b" in out and "2 * 3" in out
    assert fmt(out, profile, table_style="unchanged") == out


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("text", [
    "Use `2 \\* 3` here.",
    "Run:\n\n```\nx = 2 \\* 3\ny = a \\_ b\n```\n\nDone.",
    "Run:\n\n    x = 2 \\* 3\n\nDone.",
    "See https://x.test/a\\*b and done.",
    "See [the doc](<x \\* y>) now.",
    'An <a title="2 \\* 3">tag</a> here.',
])
def test_code_urls_and_tags_keep_their_backslashes(text, profile):
    out = fmt(text, profile)
    for fragment in ("`2 \\* 3`", "x = 2 \\* 3", "y = a \\_ b", "a\\*b", "<x \\* y>", '"2 \\* 3"'):
        if fragment in text:
            assert fragment in out
    assert_stable(out, profile)


def test_probe_reply():
    probe = ("1. In prose: the config key retry\\*limit uses an escaped asterisk.\n"
             "2. In prose: 2 \\* 3 = 6, and \\_not italic\\_.\n"
             "3. In inline code: `retry\\*limit`")
    out = fmt(probe, "markdown")
    assert "2 * 3 = 6" in out
    assert "retry\\*limit uses" in out and "\\_not italic\\_" in out and "`retry\\*limit`" in out
    assert_stable(out, "markdown")


@pytest.mark.parametrize("profile", PROFILES)
def test_ac24_only_the_spaced_escape_loses_its_backslash(profile):
    reply = ("Total 2 \\* 3 = 6 here.\n\nSet retry\\*limit and \\_name\\_, then 4 \\* 5 and 6 \\* 7.\n\n"
             "Then a \\| b and `2 \\* 3`.\n\n\\# title")
    out = fmt(reply, profile)
    assert "Total 2 * 3 = 6" in out
    for kept in ("retry\\*limit", "\\_name\\_", "4 \\* 5 and 6 \\* 7", "a \\| b", "`2 \\* 3`", "\\# title"):
        assert kept in out
    assert_stable(out, profile)


@pytest.mark.parametrize("profile", PROFILES)
def test_escape_exposed_by_emoji_removal_is_judged_on_the_first_pass(profile):
    # Fuzz seed 2640: removing the emoji turns a lone backslash into an escape.
    out = fmt("z\U0001f4a1\\\u2728)\u2728\u0631", profile)
    assert out == "z ) \u0631"
    assert_stable(out, profile)
    out = fmt("a \\\u2728) (b)", profile)
    assert "\\)" in out
    assert_stable(out, profile)
