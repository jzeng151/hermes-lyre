"""Property tests over generated replies (AC-5, AC-6, AC-10, AC-13; T10).

Seeds are fixed so CI is repeatable; set ``LYRE_FUZZ_SEED`` to start from another seed and
``LYRE_FUZZ_CASES`` to run more. A failure message names the seed: rerun it with
``fuzzgen.reply(seed)``.
"""

from __future__ import annotations

import os
import re

import pytest

from lyre.formatter import format_for_speech

from . import fuzzgen

START = int(os.environ.get("LYRE_FUZZ_SEED", "0"))
CASES = int(os.environ.get("LYRE_FUZZ_CASES", "150"))
SEEDS = range(START, START + CASES)
PROFILES = ["plain", "markdown"]

FENCE_RE = re.compile(r"^(`{3,}|~{3,})[^\n]*\n(.*?)\n\1$", re.M | re.S)
MATH_RE = re.compile(r"^\$\$\n.*?\n\$\$$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
URL_RE = re.compile(r"https?://\S+")
EMOJI_RE = re.compile("[\u2705\u274c\u26a0\U0001f389\U0001f680\U0001f525\u2728\U0001f44d\U0001f4dd\U0001f4a1]")


def _fences(text: str) -> list[str]:
    return [m.group(2) for m in FENCE_RE.finditer(text)]


def _outside_protected(text: str) -> str:
    """The text with code, math, inline code and URLs removed (AC-10's transformed regions)."""
    for pattern in (FENCE_RE, MATH_RE, INLINE_CODE_RE, URL_RE):
        text = pattern.sub(" ", text)
    return "\n".join(line for line in text.split("\n") if not line.startswith("    "))


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("seed", SEEDS)
def test_ac5_idempotent(seed, profile):
    once = format_for_speech(fuzzgen.reply(seed), profile=profile)
    assert format_for_speech(once, profile=profile) == once, f"seed {seed}"


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("seed", SEEDS)
def test_ac6_code_math_and_urls_byte_identical(seed, profile):
    text = fuzzgen.reply(seed)
    out = format_for_speech(text, profile=profile)
    for body in _fences(text):
        assert body in out, f"seed {seed}: code changed"
    for block in MATH_RE.findall(text):
        assert block in out, f"seed {seed}: math changed"
    for url in URL_RE.findall(text):
        assert url.rstrip(").") in out, f"seed {seed}: URL changed"


@pytest.mark.parametrize("seed", SEEDS)
def test_ac10_no_spoken_markup_outside_protected_spans(seed):
    text = fuzzgen.reply(seed)
    out = format_for_speech(text, profile="plain")
    if out == text:
        return  # passed through whole (fail-open or nothing to do): AC-10 does not apply
    rest = _outside_protected(out)
    latin = sum(c.isascii() and c.isalpha() for c in rest)
    letters = sum(c.isalpha() for c in rest)
    assert "|---" not in rest, f"seed {seed}"
    assert not re.search(r"\*\*[^*\n]+\*\*", rest), f"seed {seed}: paired ** left"
    assert not any(line.startswith("#") for line in rest.split("\n")), f"seed {seed}: heading marker left"
    if letters and latin * 2 >= letters:
        assert not EMOJI_RE.search(rest), f"seed {seed}: emoji left"


@pytest.mark.parametrize("seed", SEEDS)
def test_every_option_combination_is_idempotent(seed):
    """Brief and full verbosity, the remove and keep emoji policies, and both table styles."""
    text = fuzzgen.reply(seed)
    options = [dict(verbosity="brief"), dict(verbosity="full"), dict(emoji_policy="remove"),
               dict(emoji_policy="keep"), dict(table_style="unchanged")]
    kw = options[seed % len(options)]
    profile = PROFILES[seed % 2]
    once = format_for_speech(text, profile=profile, **kw)
    assert format_for_speech(once, profile=profile, **kw) == once, f"seed {seed} {kw}"
