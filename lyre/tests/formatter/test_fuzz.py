"""Fuzz tests: random Markdown punctuation and mixed scripts (AC-5, AC-13; T10).

Inputs mix Markdown symbols, emoji, joiners and variation selectors, right-to-left text,
combining marks, Braille, box drawing and CJK. The formatter must never raise, must return a
string, and must be idempotent. Seeds are fixed; ``LYRE_FUZZ_SEED`` and ``LYRE_FUZZ_CASES``
move or widen the range.
"""

from __future__ import annotations

import os

import pytest

from lyre.formatter import format_for_speech

from . import fuzzgen

START = int(os.environ.get("LYRE_FUZZ_SEED", "0"))
CASES = int(os.environ.get("LYRE_FUZZ_CASES", "150"))


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("seed", range(START, START + CASES))
def test_soup_never_raises_and_is_idempotent(seed, profile):
    text = fuzzgen.soup(seed)
    errors = []
    once = format_for_speech(text, profile=profile, on_error=errors.append)
    assert isinstance(once, str), f"seed {seed}"
    assert not errors, f"seed {seed}: a rule raised {errors[0]!r}"
    assert format_for_speech(once, profile=profile) == once, f"seed {seed}"


@pytest.mark.parametrize("text", ["\u202emirrored **text**\u202c", "a\u0300\u0301\u0302\u0303" * 50,
                                  "\U0001f469\u200d\U0001f4bb **dev**", "\ufeff# Title", "\x00**x**"])
def test_unusual_code_points_do_not_raise(text):
    errors = []
    out = format_for_speech(text, profile="plain", on_error=errors.append)
    assert not errors
    assert format_for_speech(out, profile="plain") == out
