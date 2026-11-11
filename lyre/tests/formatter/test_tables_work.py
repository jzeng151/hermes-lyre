"""Bound table safety work without bypassing restored-output validation."""

import importlib

import pytest

from lyre.formatter import format_for_speech
from lyre.formatter.model import Block


tables = importlib.import_module("lyre.formatter.rules.tables")


@pytest.mark.parametrize("cell", ["Name", "Price", "Alpha", "$10", "[label]", "a > b", "\\*literal\\*"])
def test_harmless_cells_do_not_repeat_span_protection(monkeypatch, cell):
    def unexpected(*args, **kwargs):
        raise AssertionError("cell has no delimiter that can become unsafe")

    monkeypatch.setattr(tables, "protect_code_spans", unexpected)
    monkeypatch.setattr(tables, "protect_inline", unexpected)
    assert not tables._unsafe_cell(cell, Block("table", []))


def test_plain_table_still_validates_every_restored_output_line(monkeypatch):
    seen = []
    original = tables.inline_rules

    def record(text, opts):
        seen.append(text)
        return text

    monkeypatch.setattr(tables, "inline_rules", lambda: [*original(), record])
    text = "| Name | Price |\n|---|---|\n| Alpha | $10 |"
    expected = "Table, 1 row, 2 columns: Name, Price.\nRow 1: Name Alpha, Price $10.\nEnd of table."
    assert format_for_speech(text, profile="plain") == expected
    assert seen == expected.splitlines()


def test_restored_validation_snapshots_rules_once_for_all_rows(monkeypatch):
    calls = 0
    original = tables.inline_rules

    def snapshot():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(tables, "inline_rules", snapshot)
    text = "| Name | Price |\n|---|---|\n" + "\n".join("| Alpha | $10 |" for _ in range(50))
    result = format_for_speech(text, profile="plain", verbosity="full")
    assert result.startswith("Table, 50 rows, 2 columns: Name, Price.")
    assert "Row 50: Name Alpha, Price $10." in result
    assert calls == 1
