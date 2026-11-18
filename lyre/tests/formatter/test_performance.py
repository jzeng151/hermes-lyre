"""Performance (AC-8, AC-9; T12).

The 20 KB fixture is built from generated replies, so it mixes every rule. The budget is
100 ms on CI hardware (ADR 0006); a desktop takes about a third of that. Timing on shared
runners varies, so the test takes the best of three calls: a real slowdown (a quadratic path)
still fails, a scheduler pause does not. The worst case for the pipeline is many small blocks,
because every block runs segmentation, protection and the guard.
"""

from __future__ import annotations

import time

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


def assert_scales_linearly(reply, n: int = 1_000, ceiling_s: float = 2.0) -> None:
    """Fail when 8x the input costs far more than 8x the time.

    Linear work grows about 8x and quadratic work about 64x, so a 24x limit separates them with
    room for noisy shared runners; a single timed run can stall several-fold on macOS. Best of
    three runs on each size, plus an absolute ceiling on the larger one.
    """
    small = _best_of(reply(n))
    large = _best_of(reply(8 * n))
    assert large < ceiling_s
    assert large < 24 * max(small, 0.005), (small, large)


def test_link_targets_math_and_code_runs_scale_linearly():
    # Link destinations, display math and two backtick runs on one line used to rebuild the
    # exclusion ranges once per math span, so a 104 KB line took several seconds.
    assert_scales_linearly(lambda n: "[a](b) " * n + "$$x$$ " * n + "`code` `more`")


def test_ac8_one_megabyte_is_skipped_not_processed():
    text = _fixture(20_000) * 50
    assert len(text.encode()) > 200_000
    start = time.perf_counter()
    assert format_for_speech(text, profile="plain") is text
    # Processing would take seconds; the skip only measures the size. 5 ms was within noise of
    # the UTF-8 size check on macOS runners (5.2 and 5.5 ms observed).
    assert time.perf_counter() - start < 0.05
