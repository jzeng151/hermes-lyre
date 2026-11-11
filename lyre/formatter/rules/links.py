"""R8: links and images (both profiles).

``[docs](https://x.test)`` becomes ``docs, link: https://x.test`` and ``![chart](u)`` becomes
``Image: chart, link: u``; a linked image (``[![alt](src)](href)``) becomes
``Image: alt, source: src, link: href``. URLs are never shortened or re-encoded. A label equal to
its URL and ``<https://x.test>`` become the bare URL. A destination that the next pass would not
protect as a URL (a relative path, a fragment, another scheme) keeps the link as written, so no
pass can change it. Mostly non-Latin replies keep markdown links. Inline code keeps its backticks
(spec R8, Q5). This rule runs after every other inline rule.
"""

from __future__ import annotations

import re

from ..model import Options
from ..spans import OPEN, TOKEN_RE, Stash, protect_inline
from . import register_inline_rule

_T = "\ue000t\\d+\ue001"
# An optional outer ``[`` with a matching ``](target)`` makes a linked image one unit.
_LINK_RE = re.compile(f"(\\[)?(!?)\\[([^\\[\\]\n]*)\\]\\(({_T})\\)(?(1)\\]\\(({_T})\\))")
_AUTOLINK_RE = re.compile("<(\ue000u\\d+\ue001)>")


def _target_url(value: str) -> str:
    """The URL part of a link target, without angle brackets or a title."""
    value = value.strip()
    if value.startswith("<") and ">" in value:
        return value[1:value.index(">")]
    parts = value.split()
    return parts[0] if parts else value


def _survives(url: str) -> bool:
    """True when the next pass protects *url* whole as a bare URL, so no rule can change it."""
    stash = Stash()
    token = protect_inline(url, stash)
    return bool(TOKEN_RE.fullmatch(token)) and stash.value_of(token) == url


def links(text: str, opts: Options) -> str:
    if OPEN not in text:
        return text
    text = _AUTOLINK_RE.sub(r"\1", text)
    if not opts.latin or opts.span is None:
        return text
    span = opts.span

    def replace(m: re.Match) -> str:
        values = [span(m.group(4)), span(m.group(5)) if m.group(1) else ""]
        if None in values:
            return m.group(0)
        urls = [_target_url(value) for value in values if value]
        if not all(_survives(url) for url in urls):
            return m.group(0)
        label = m.group(3).strip()  # tokens stay tokens; only the comparison expands them
        shown = span(label) if TOKEN_RE.fullmatch(label) else label
        if m.group(1):
            name = f"Image: {label}" if label else "Image"
            prefix = f"{name}, source: {urls[0]}, link: {urls[1]}"
            return prefix if m.group(2) else m.group(0)
        if m.group(2):
            return f"Image: {label}, link: {urls[0]}" if label else f"Image, link: {urls[0]}"
        if not label or shown == urls[0]:
            return label or urls[0]
        return f"{label}, link: {urls[0]}"

    return _LINK_RE.sub(replace, text)


register_inline_rule("links", links, order=90)
