from lyre.formatter import format_for_speech


def test_plain_prose_is_unchanged():
    text = "The tests passed. Two files changed."
    assert format_for_speech(text, platform="telegram") == text
