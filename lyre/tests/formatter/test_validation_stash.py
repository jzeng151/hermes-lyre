"""Fresh table-validation spans must use their own destination stash."""

from lyre.formatter import format_for_speech
from lyre.formatter.rules import tables


def test_table_validation_binds_url_protection_to_validation_stash(monkeypatch):
    checked = []

    def check(text, opts):
        url = "https://example.test/a~~literal~~b"
        token = opts.protect_url(url)
        checked.append(opts.span(token))
        return text

    monkeypatch.setattr(tables, "inline_rules", lambda: (check,))
    once = format_for_speech("| A |\n|---|\n| x |", profile="plain")
    assert once.startswith("Table,")
    assert checked and all(value == "https://example.test/a~~literal~~b" for value in checked)
