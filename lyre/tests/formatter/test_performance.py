"""Performance (AC-8, AC-9; T12).

The 20 KB fixture is built from generated replies, so it mixes every rule. The budget is
100 ms on CI hardware (ADR 0006); a desktop takes about a third of that. Timing on shared
runners varies, so the test takes the best of three calls: a real slowdown (a quadratic path)
still fails, a scheduler pause does not. The worst case for the pipeline is many small blocks,
because every block runs segmentation, protection and the guard.
"""

from __future__ import annotations

import time

import pytest

from lyre.formatter import format_for_speech

from . import fuzzgen

BUDGET_S = 0.1  # ADR 0006


def _fixture(size: int) -> str:
    parts, seed = [], 0
    while sum(len(p) + 2 for p in parts) < size:
        parts.append(fuzzgen.reply(seed))
        seed += 1
    return "\n\n".join(parts)[:size]


def _best_of(text: str, runs: int = 3) -> float:
    format_for_speech(text, profile="plain")  # warm the regex caches
    best = float("inf")
    for _ in range(runs):
        start = time.perf_counter()
        format_for_speech(text, profile="plain")
        best = min(best, time.perf_counter() - start)
    return best


def test_ac9_twenty_kb_mixed_reply_within_budget():
    assert _best_of(_fixture(20_000)) < BUDGET_S


def test_link_targets_math_and_code_runs_scale_linearly():
    # Link destinations, display math and two backtick runs on one line used to rebuild the
    # exclusion ranges once per math span, so a 104 KB line took several seconds.
    def reply(n: int) -> str:
        return "[a](b) " * n + "$$x$$ " * n + "`code` `more`"

    small = _best_of(reply(2_000), runs=1)
    large = _best_of(reply(8_000), runs=1)
    assert large < 2.0
    assert large < 8 * max(small, 0.01)  # 4x the input: linear is ~4x, quadratic ~16x


# Adversarial inline-math lines (ADR 0009): every candidate opener must stop at the next
# opener of its kind, or a line of them scans to its end once per opener.
MATH_LINES = {
    "escaped dollars": lambda n: "x \\$5 " * n,
    "dollar openers before spaces": lambda n: "$a b " * n,
    "unclosed paren openers": lambda n: "\\( a " * n,
    "escaped paren openers, one close": lambda n: "\\\\( a " * n + "\\)",
    "unclosed bracket openers": lambda n: "\\[ a " * n,
    "escaped bracket openers, one close": lambda n: "\\\\[ a " * n + "\\]",
    "math rejected into destinations": lambda n: "[x](u/$a)$ " * n,
    "paren math rejected into URLs": lambda n: "\\(https://x.test/a\\) " * n,
}


@pytest.mark.parametrize("name", sorted(MATH_LINES))
def test_inline_math_candidates_scale_linearly(name):
    reply = MATH_LINES[name]
    small = _best_of(reply(2_000), runs=1)
    large = _best_of(reply(8_000), runs=1)
    assert large < 1.0
    assert large < 8 * max(small, 0.01)  # 4x the input: linear is ~4x, quadratic ~16x


def test_escaped_dollar_prose_within_budget():
    text = "Costs \\$5 each, " * 1_100  # about 17.6 KB on one line
    assert _best_of(text) < BUDGET_S


def test_ac8_one_megabyte_is_skipped_not_processed():
    text = _fixture(20_000) * 50
    assert len(text.encode()) > 200_000
    start = time.perf_counter()
    assert format_for_speech(text, profile="plain") is text
    assert time.perf_counter() - start < 0.005
