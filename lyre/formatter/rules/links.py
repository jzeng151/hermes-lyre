"""R8: links and images (both profiles).

``[docs](https://x.test)`` becomes ``docs, link: https://x.test`` and ``![chart](u)`` becomes
``Image: chart, link: u``. URLs are never shortened or re-encoded. A label equal to its URL and
``<https://x.test>`` become the bare URL. Mostly non-Latin replies keep markdown links. Inline
code keeps its backticks (spec R8, Q5). This rule runs after every other inline rule, so the URL
it writes into the line is not touched again in this pass; the next pass protects it as a URL.
"""

from __future__ import annotations

import re

from ..model import Options
from ..spans import OPEN, TOKEN_RE
from . import register_inline_rule

_LINK_RE = re.compile("(!?)\\[([^\\[\\]\n]*)\\]\\((\ue000t\\d+\ue001)\\)")
_AUTOLINK_RE = re.compile("<(\ue000u\\d+\ue001)>")


def _target_url(value: str) -> str:
    """The URL part of a link target, without angle brackets or a title."""
    value = value.strip()
    if value.startswith("<") and ">" in value:
        return value[1:value.index(">")]
    parts = value.split()
    return parts[0] if parts else value


def links(text: str, opts: Options) -> str:
    if OPEN not in text:
        return text
    text = _AUTOLINK_RE.sub(r"\1", text)
    if not opts.latin or opts.span is None:
        return text
    span = opts.span

    def replace(m: re.Match) -> str:
        value = span(m.group(3))
        if value is None:
            return m.group(0)
        url, label = _target_url(value), m.group(2).strip()
        if TOKEN_RE.fullmatch(label):
            label = span(label) or label  # a label that is itself a URL or code span
        if m.group(1):
            return f"Image: {label}, link: {url}" if label else f"Image, link: {url}"
        if not label or label == url:
            return url
        return f"{label}, link: {url}"

    return _LINK_RE.sub(replace, text)


register_inline_rule("links", links, order=90)
