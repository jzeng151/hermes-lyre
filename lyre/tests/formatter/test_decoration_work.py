"""Work bounds for the drawing-only rule on ordinary prose."""

from lyre.formatter.model import Options
from lyre.formatter.rules import decoration


def test_drawing_rule_rejects_prose_before_scanning_the_line(monkeypatch):
    original = decoration._is_drawing
    checked = []

    def track(ch):
        checked.append(ch)
        return original(ch)

    monkeypatch.setattr(decoration, "_is_drawing", track)
    text = "Prose " + "\u2500" * 20_000
    assert decoration.drawing_only(text, Options(profile="plain")) == text
    assert len(checked) <= 1
