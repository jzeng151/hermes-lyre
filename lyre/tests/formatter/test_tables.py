"""R6 tables (task T6)."""

from __future__ import annotations

import pytest

from lyre.formatter import format_for_speech

SPEC = "| Name  | Price | Stock |\n|-------|------:|-------|\n| Alpha | $10   | 4     |\n| Beta  | $12   |       |"


def plain(text: str, **kw) -> str:
    return format_for_speech(text, profile="plain", **kw)


def table(rows: int, cols: int = 2, cell: str = "v") -> str:
    head = "| " + " | ".join(f"H{c}" for c in range(cols)) + " |"
    sep = "|" + "---|" * cols
    body = ["| " + " | ".join(f"{cell}{r}_{c}" for c in range(cols)) + " |" for r in range(rows)]
    return "\n".join([head, sep, *body])


def test_spec_example_normal():
    assert plain(SPEC) == ("Table, 2 rows, 3 columns: Name, Price, Stock.\n"
                           "Row 1: Name Alpha, Price $10, Stock 4.\n"
                           "Row 2: Name Beta, Price $12, Stock blank.\nEnd of table.")


def test_brief():
    assert plain(SPEC, verbosity="brief") == ("Table, 2 rows: Name, Price, Stock.\n"
                                              "Row 1: Alpha, $10, 4.\nRow 2: Beta, $12, blank.")


def test_full_repeats_columns_every_tenth_row():
    out = plain(table(21), verbosity="full").split("\n")
    assert out.count("Columns: H0, H1.") == 2
    assert out[out.index("Columns: H0, H1.") + 1].startswith("Row 10:")


def test_ac1_nine_rows_keep_every_cell_in_order():
    text = table(9)
    out = plain(text)
    positions = [out.index(f"v{r}_{c}") for r in range(9) for c in range(2)]
    assert positions == sorted(positions)
    assert "Row 9: H0 v8_0, H1 v8_1." in out


@pytest.mark.parametrize("text", [
    "| a | b |\n| 1 | 2 |",                                      # no separator row
    "| a |\n|---|\n| 1 | 2 |",                                   # body row wider than header
    table(51),                                                   # more than 50 rows
    table(1, cols=11),                                           # more than 10 columns
    table(1, cell="x" * 501),                                    # a cell over 500 characters
])
def test_ac2_malformed_and_oversized_tables_byte_identical(text):
    out = plain(text)
    assert all(line in out.split("\n") for line in text.split("\n") if "|" in line)


def test_cells_get_inline_rules_and_keep_protected_spans():
    text = "| a \\| b | **c** |\n|---|---|\n| `x|y` | ✅ |"
    assert plain(text) == "Table, 1 row, 2 columns: a | b, c.\nRow 1: a | b `x|y`, c (done).\nEnd of table."


def test_short_rows_padded_and_headerless_column_named():
    assert plain("| A | |\n|---|---|\n| short |") == (
        "Table, 1 row, 2 columns: A, Column 2.\nRow 1: A short, Column 2 blank.\nEnd of table.")


def test_no_leading_pipes():
    assert plain("a|b\n---|---\n1|2") == "Table, 1 row, 2 columns: a, b.\nRow 1: a 1, b 2.\nEnd of table."


def test_non_latin_table_passes_through():
    text = "| Имя | Цена |\n|---|---|\n| Альфа | 10 |"
    assert plain(text) == text


def test_unchanged_style_only_cleans_cells():
    assert plain("| **a** |\n|---|\n| 1 |", table_style="unchanged") == "| a |\n|---|\n| 1 |"


def test_markdown_profile_also_speaks_tables():
    assert format_for_speech(SPEC, profile="markdown").startswith("Table, 2 rows, 3 columns")


@pytest.mark.parametrize("text", [SPEC, table(9), table(21), "a|b\n---|---\n1|2", "| a |\n|---|\n| 1 | 2 |"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_idempotent(text, verbosity):
    once = plain(text, verbosity=verbosity)
    assert plain(once, verbosity=verbosity) == once


def test_bare_url_ends_at_cell_boundary():
    assert plain("|A|B|\n|---|---|\n|https://x.test|secret|") == (
        "Table, 1 row, 2 columns: A, B.\nRow 1: A https://x.test, B secret.\nEnd of table.")


def test_cell_limit_measures_protected_text():
    text = "| A |\n|---|\n| `" + "x" * 501 + "` |"
    assert plain(text) == text


def test_markers_paired_across_cells_keep_table():
    text = "| A | B |\n|---|---|\n| *alpha | beta* |"
    assert plain(text) == text


def test_pipe_less_short_row_is_a_row():
    assert plain("| A | B |\n|---|---|\nshort\n| next | value |") == (
        "Table, 2 rows, 2 columns: A, B.\nRow 1: A short, B blank.\nRow 2: A next, B value.\nEnd of table.")


@pytest.mark.parametrize("text", [
    "| A | B |\n|---|\n| x | y |",                    # separator narrower than the header
    "| A | `✅` |\n|---|---|\n| ` | x |",              # a stray backtick could pair across cells
])
def test_review_round_two_pass_through(text):
    assert plain(text) == text


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_link_target_backtick_cannot_capture_code_in_later_row(profile, verbosity):
    text = "| A |\n|---|\n| [link](foo`bar) |\n| `✅` |"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_incomplete_html_header_cannot_capture_repeated_column_label(profile, verbosity):
    text = "| >* | <a x |\n|---|---|\n| | x |"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("text", [
    "| A | B |\n|---|---|\n| *a $$ **b | c $$ d* |",
    "| $$ | B |\n|---|---|\n| *a | b* $$ |",
    "| A | B |\n|---|---|\n| *a $$ | b |\n| c | $$ d* |",
    "| A | B |\n|---|---|\n| *a $$$$ **b | c $$ d* |",
    "| A | B |\n|---|---|\n| *a \\$$ **b | c $$ d* |",
    "| A | B |\n|---|---|\n| *a $\\$ **b | c $$ d* |",
    "| \\$$ | B |\n|---|---|\n| **a** | b |",
])
def test_unmatched_math_keeps_cell_boundaries(text, profile, verbosity):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("cell", [
    "$$**literal**$$",
    "`$$`",
    "https://x.test/$$",
    "[x](foo$$bar)",
    '<a title="$$">',
    "$5",
    r"$\$",
    "$`literal`$",
])
def test_complete_or_protected_math_still_speaks_tables(cell, profile, verbosity):
    text = f"| A |\n|---|\n| {cell} |"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once.startswith("Table, 1 row")
    assert cell in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


def test_table_after_paragraph_line():
    assert plain("Results:\n| A | B |\n|---|---|\n|1|2|") == (
        "Results:\n\nTable, 1 row, 2 columns: A, B.\nRow 1: A 1, B 2.\nEnd of table.")


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("text", [
    "| A | ) |\n|---|---|\n| *a | [x](foo |\n| x | b* |",
    "| )* | [x]( |\n|---|---|\n| | x |",
    "| A | ) |\n|---|---|\n| *a | ![x](foo(bar |\n| x | b* |",
])
def test_incomplete_link_target_keeps_cell_boundaries(text, profile, verbosity):
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("destination", ["", " /path", " /path/**literal**"])
def test_reference_destination_keeps_cell_boundaries(profile, verbosity, destination):
    text = f"| A | [x]:{destination} |\n|---|---|\n| x | /destination |"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once == text
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("cell", [
    "[x](foo(bar))",
    "[x](<foo bar>)",
    '[x](foo "title (ok)")',
    "[x]()",
    "`[x](`",
    "$$[x]($$",
    '<a title="[x](">',
    "https://x.test/[x](",
    r"[x]\(",
    r"[x\](",
])
def test_complete_or_protected_link_openers_still_speak_tables(cell, profile, verbosity):
    text = f"| A |\n|---|\n| {cell} |"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    if cell == "https://x.test/[x](":
        # Link-label URL protection exposes the trailing opener at this layer; fail open.
        assert once == text
    else:
        assert once.startswith("Table, 1 row")
    assert cell in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
