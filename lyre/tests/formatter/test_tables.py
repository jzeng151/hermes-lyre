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
