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
from ..spans import CLOSE, OPEN, TOKEN_RE, Stash, protect_inline
from . import register_inline_rule

_T = "\ue000t\\d+\ue001"
# An optional outer ``[`` with a matching ``](target)`` makes a linked image one unit.
_LINK_RE = re.compile(f"(\\[)?(!?)\\[([^\\[\\]\n]*)\\]\\(({_T})\\)(?(1)\\]\\(({_T})\\))")
_URL_END = ".,;:!?)'\"*_"  # characters the next pass never takes into a bare URL
_AUTOLINK_RE = re.compile("<(\ue000u\\d+\ue001)>")


def _target_url(value: str) -> str:
    """The URL part of a link target, without angle brackets or a title."""
    value = value.strip()
    if value.startswith("<") and ">" in value:
        return value[1:value.index(">")]
    parts = value.split()
    return parts[0] if parts else value


def _glued(m: re.Match) -> bool:
    """True when text directly after the match would run into a URL emitted in its place."""
    after = m.string[m.end():m.end() + 1]
    return bool(after) and not after.isspace() and after not in _URL_END


def _survives(url: str) -> bool:
    """True when the next pass protects *url* whole as a bare URL, so no rule can change it."""
    if OPEN in url or CLOSE in url:
        return False  # already holds a protected span (``<guide>`` as HTML): not a bare URL
    stash = Stash()
    token = protect_inline(url, stash)
    return bool(TOKEN_RE.fullmatch(token)) and stash.value_of(token) == url


def links(text: str, opts: Options) -> str:
    if OPEN not in text:
        return text
    # Removing the brackets must not glue following text onto the URL (``<u>suffix``).
    text = _AUTOLINK_RE.sub(lambda m: m.group(1) + (" " if _glued(m) else ""), text)
    if not opts.latin or opts.span is None:
        return text
    span = opts.span

    def replace(m: re.Match) -> str:
        values = [span(m.group(4)), span(m.group(5)) if m.group(1) else "x"]
        if None in values or not all(value.strip() for value in values):
            return m.group(0)  # unknown token or an empty destination (``[back]()``)
        values = values if m.group(1) else values[:1]
        urls = [_target_url(value) for value in values if value]
        if not all(_survives(url) for url in urls):
            return m.group(0)
        label = m.group(3).strip()  # tokens stay tokens; only the comparison expands them
        shown = span(label) if TOKEN_RE.fullmatch(label) else label
        # Block rules may run inline validation again before the core restores tokens.
        # Keep emitted destinations opaque throughout that entire container pass.
        protected = [opts.protect_url(url) if opts.protect_url else url for url in urls]
        if m.group(1):
            name = f"Image: {label}" if label else "Image"
            prefix = f"{name}, source: {protected[0]}, link: {protected[1]}"
            return prefix if m.group(2) else m.group(0)
        if m.group(2):
            return f"Image: {label}, link: {protected[0]}" if label else f"Image, link: {protected[0]}"
        if not label or shown == urls[0]:
            return label or protected[0]
        return f"{label}, link: {protected[0]}"

    def bounded(m: re.Match) -> str:
        out = replace(m)
        # Text glued to the link (``](u)suffix``, ``](u)[b](v)``) must not join the emitted URL.
        if out != m.group(0) and _glued(m):
            out += " "
        return out

    return _LINK_RE.sub(bounded, text)


register_inline_rule("links", links, order=90)
