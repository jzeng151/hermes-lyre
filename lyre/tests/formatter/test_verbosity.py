"""Verbosity levels across every rule (task T9, AC-12)."""

from __future__ import annotations

import re

import pytest

from lyre.formatter import format_for_speech

LEVELS = ("brief", "normal", "full")

# rule: (input, {level: expected plain output})
MATRIX = {
    "emphasis": ("~~old~~ **new**", dict.fromkeys(LEVELS, "(removed: old) new")),
    "heading": ("# Results", {"brief": "Results.", "normal": "Results.", "full": "Heading: Results."}),
    "subheading": ("### Detail", {"brief": "Detail.", "normal": "Detail.", "full": "Subheading: Detail."}),
    "decoration": ("a\n\n---\n\nb", dict.fromkeys(LEVELS, "a\n\nb")),
    "emoji": ("✅ done 🎉", dict.fromkeys(LEVELS, "(done) done")),
    "list": ("- a\n- b\n  - c", {
        "brief": "1, a\n2, b\n  sub-item 1, c",
        "normal": "2 items.\n1, a\n2, b\n  1 sub-item.\n  sub-item 1, c",
        "full": "List, 2 items.\n1, a\n2, b\n  Sub-list, 1 item.\n  sub-item 1, c\nEnd of list.",
    }),
    "table": ("| N | P |\n|---|---|\n| A | 1 |", {
        "brief": "Table, 1 row: N, P.\nRow 1: A, 1.",
        "normal": "Table, 1 row, 2 columns: N, P.\nRow 1: N A, P 1.\nEnd of table.",
        "full": "Table, 1 row, 2 columns: N, P.\nRow 1: N A, P 1.\nEnd of table.",
    }),
    "code": ("```py\nx = 1\n```", {
        "brief": "Code:\n```py\nx = 1\n```\nEnd of code.",
        "normal": "Python code, 1 line:\n```py\nx = 1\n```\nEnd of code.",
        "full": "Python code, 1 line:\n```py\nx = 1\n```\nEnd of code.",
    }),
    "link": ("[docs](https://x.test)", dict.fromkeys(LEVELS, "docs, link: https://x.test")),
    "quote": ("> hi **there**", {"brief": "hi there", "normal": "hi there", "full": "Quote:\nhi there\nEnd of quote."}),
}


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("rule", sorted(MATRIX))
def test_rule_at_level(rule, level):
    text, expected = MATRIX[rule]
    once = format_for_speech(text, profile="plain", verbosity=level)
    assert once == expected[level]
    assert format_for_speech(once, profile="plain", verbosity=level) == once


MIXED = """# Release notes

Status ✅ for **build**, see [the docs](https://x.test/docs?a=1&b=2).

| Name  | Price | Stock |
|-------|------:|-------|
| Alpha | $10   | 4     |
| Beta  | $12   |       |

- Build
- Test
  - unit
  - live

```python
print("✅ **done** | x")
```

> Quoted *note* with `code`.
"""

CELLS = ["Name", "Price", "Stock", "Alpha", "$10", "4", "Beta", "$12"]
URLS = ["https://x.test/docs?a=1&b=2"]
CODE = ['print("✅ **done** | x")', "`code`"]
WORDS = ["Release notes", "build", "the docs", "Build", "Test", "unit", "live", "Quoted note"]


@pytest.mark.parametrize("profile", ["plain", "markdown"])
def test_ac12_every_level_keeps_all_information(profile):
    outputs = {level: format_for_speech(MIXED, profile=profile, verbosity=level) for level in LEVELS}
    for level, out in outputs.items():
        for needle in CELLS + URLS + CODE:
            assert needle in out, (level, needle)
        if profile == "plain":
            flat = re.sub(r"\s+", " ", out)
            for word in WORDS:
                assert word in flat, (level, word)
        assert "(done)" in out
        assert format_for_speech(out, profile=profile, verbosity=level) == out


def test_levels_only_change_framing():
    """Removing each level's framing lines leaves the same content lines."""
    framing = re.compile(r"^(?:\d+ (?:sub-)?items?\.|List, .*|Sub-list, .*|End of (?:list|table|code|quote)\.|"
                         r"Quote:|Table, .*|Code:|\w+ code, \d+ lines?:|Heading: |Columns: .*)$")

    def content(level: str) -> list[str]:
        out = format_for_speech(MIXED, profile="plain", verbosity=level)
        lines = [line.strip() for line in out.split("\n") if line.strip() and not framing.match(line.strip())]
        # brief rows drop the column names; keep only the values for the comparison
        return [re.sub(r"^Row (\d+): .*", r"Row \1", line).replace("Heading: ", "") for line in lines]

    assert content("brief") == content("normal") == content("full")
