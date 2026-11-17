"""Golden corpus (T11): synthetic replies modelled on real Hermes output, with reviewed output.

Any change to the formatter's output fails here. If the change is intended, regenerate with
``python tests/golden/update_golden.py`` and review the diff: a changed code or URL byte is a bug.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from lyre.formatter import format_for_speech

GOLDEN = Path(__file__).resolve().parents[1] / "golden"
_spec = importlib.util.spec_from_file_location("update_golden", GOLDEN / "update_golden.py")
assert _spec and _spec.loader
update_golden = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_golden)

CASES = sorted((GOLDEN / "cases").glob("*.md"))
PROFILES = update_golden.PROFILES


def test_corpus_size():
    assert 30 <= len(CASES) <= 50


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.stem)
def test_output_matches_golden(case, profile):
    expected = update_golden.expected_path(case, profile).read_bytes().decode("utf-8").removesuffix("\n")
    assert format_for_speech(update_golden.read_case(case), profile=profile) == expected


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.stem)
def test_golden_output_is_stable_and_keeps_code_and_urls(case, profile):
    text = update_golden.read_case(case)
    expected = update_golden.expected_path(case, profile).read_bytes().decode("utf-8").removesuffix("\n")
    assert format_for_speech(expected, profile=profile) == expected
    for body in re.findall(r"```[^\n]*\n(.*?)\n\s*```", text, flags=re.S):
        lines = [line.strip() for line in body.split("\n")]
        assert all(line in expected for line in lines), "code changed"
    for url in re.findall(r"https?://[^\s)>]+", text):
        assert url in expected, "URL changed"
