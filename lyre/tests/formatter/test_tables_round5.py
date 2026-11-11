"""Table conversion preserves inline protection after restoring destinations."""

import pytest

from lyre.formatter import format_for_speech


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
def test_hidden_math_cannot_repair_markers_across_cells(profile, verbosity):
    text = "| A | B |\n|---|---|\n| *a [x](foo$$bar) **b | c [y](baz$$qux) d* |"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
    if profile == "plain":
        assert once == text


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("side", ["before", "after"])
def test_converted_table_keeps_paragraph_boundaries(profile, verbosity, side):
    table = "| A |\n|---|\n| `✅` |"
    text = "Before `\n" + table if side == "before" else table + "\n# After `"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
    assert "`✅`" in once
    if side == "before":
        assert once.startswith("Before `\n\nTable,")
    else:
        assert ".\n\n" in once


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("cell", [
    "$$**literal**$$",
    "[x](foo$$bar)",
    "`$$`",
    "https://x.test/$$",
    "[download](https://x.test/a~~file~~b)",
])
def test_restored_validation_keeps_safe_protected_cells(cell, profile, verbosity):
    text = f"| A |\n|---|\n| {cell} |"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once.startswith("Table, 1 row")
    if "https://" in cell:
        assert cell.removeprefix("[download](").removesuffix(")") in once
    else:
        assert cell in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
