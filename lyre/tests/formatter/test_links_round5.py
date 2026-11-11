"""Emitted link destinations remain protected through table validation."""

import pytest

from lyre.formatter import format_for_speech


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("label", ["download", "", "https://x.test/a~~file~~b"])
def test_table_renders_link_without_reinterpreting_destination(profile, verbosity, label):
    url = "https://x.test/a~~file~~b"
    text = f"| File |\n|---|\n| [{label}]({url}) |"
    once = format_for_speech(text, profile=profile, verbosity=verbosity)
    assert once.startswith("Table, 1 row")
    assert url in once
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
