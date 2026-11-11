"""Regenerate the golden corpus expectations (T11).

Usage, from the plugin folder: python tests/golden/update_golden.py

Writes ``expected/<case>.plain.txt`` and ``expected/<case>.markdown.txt`` for every
``cases/<case>.md``. Review the diff before committing: a changed code or URL byte is a bug.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))  # the plugin's parent, so ``lyre`` imports

from lyre.formatter import format_for_speech  # noqa: E402

PROFILES = ("plain", "markdown")


def expected_path(case: Path, profile: str) -> Path:
    return HERE / "expected" / f"{case.stem}.{profile}.txt"


def read_case(case: Path) -> str:
    return case.read_bytes().decode("utf-8").removesuffix("\n")


def main() -> None:
    (HERE / "expected").mkdir(exist_ok=True)
    cases = sorted((HERE / "cases").glob("*.md"))
    for case in cases:
        text = read_case(case)
        for profile in PROFILES:
            expected_path(case, profile).write_bytes((format_for_speech(text, profile=profile) + "\n").encode("utf-8"))
    print(f"wrote {len(cases) * len(PROFILES)} expected outputs for {len(cases)} cases")


if __name__ == "__main__":
    main()
