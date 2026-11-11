"""Protected adjacent fences are not ambiguous indented prose."""
import pytest

from lyre.formatter import format_for_speech


@pytest.mark.parametrize("profile", ["plain", "markdown"])
@pytest.mark.parametrize("verbosity", ["brief", "normal", "full"])
@pytest.mark.parametrize("indent", ["    ", "\t"])
def test_adjacent_protected_fences_both_labelled_first_pass(profile, verbosity, indent):
    first = "```py\nx\n```"
    second = indent + "```py\n" + indent + "y\n" + indent + "```"
    once = format_for_speech(first + "\n" + second, profile=profile, verbosity=verbosity)
    assert first in once and second in once
    assert once.count("End of code.") == 2
    assert format_for_speech(once, profile=profile, verbosity=verbosity) == once
