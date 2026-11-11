"""Seeded reply generator shared by the property and fuzz tests (standard library only).

``reply(seed)`` builds a Markdown reply from fragments a model writes: headings, lists, tables,
fenced and indented code, display math, links, bare URLs, emoji, quotes, Braille, box drawing,
right-to-left text and combining marks. Every fragment is well formed, and fragments are joined
by blank lines, so each property failure points at a formatter bug rather than at ambiguous input.
``soup(seed)`` is the opposite: random characters drawn from Markdown punctuation and assorted
scripts, for the no-crash and fail-open checks.
"""

from __future__ import annotations

import random

WORDS = ["build", "tests", "passed", "config", "deploy", "error", "retry", "cache", "server",
         "update", "notes", "branch", "release", "token", "queue", "result", "value", "check"]
EMOJI = ["✅", "❌", "⚠️", "🎉", "🚀", "🔥", "✨", "👍", "📝", "💡"]
URLS = ["https://example.test/a?b=1&c=2", "https://x.test/path/**literal**/_x_",
        "https://s3.example.test/bucket/key?X-Amz-Signature=abc123def456&X-Amz-Expires=3600"]
LANGS = ["py", "js", "bash", ""]
RTL = ["مرحبا بالعالم", "שלום עולם"]
COMBINING = ["e\u0301te\u0301", "na\u0308ive", "Z\u0335a\u0336l\u0337g\u0338o"]
BRAILLE = "⠓⠑⠇⠇⠕ ⠺⠕⠗⠇⠙"
TREE = ["├── src", "│   └── main.py", "└── README.md"]


def _words(rng: random.Random, n: int) -> str:
    return " ".join(rng.choice(WORDS) for _ in range(n))


def _prose(rng: random.Random) -> str:
    parts = [_words(rng, rng.randint(2, 5))]
    for _ in range(rng.randint(1, 4)):
        kind = rng.randrange(9)
        w = _words(rng, rng.randint(1, 3))
        if kind == 0:
            parts.append(f"**{w}**")
        elif kind == 1:
            parts.append(f"*{w}*")
        elif kind == 2:
            parts.append(f"`{w} ** x`")
        elif kind == 3:
            parts.append(f"[{w}]({rng.choice(URLS)})")
        elif kind == 4:
            parts.append(rng.choice(URLS))
        elif kind == 5:
            parts.append(rng.choice(EMOJI))
        elif kind == 6:
            parts.append(f"~~{w}~~")
        elif kind == 7:
            parts.append(rng.choice(COMBINING))
        else:
            parts.append(_words(rng, 2))
    return " ".join(parts) + "."


def _code(rng: random.Random) -> str:
    body = [f"x = '{rng.choice(EMOJI)} **{rng.choice(WORDS)}** | # {rng.choice(WORDS)}'",
            "if x:", "    print(x)  # | --- |"][: rng.randint(1, 3)]
    fence = rng.choice(["```", "~~~", "````"])
    return "\n".join([fence + rng.choice(LANGS), *body, fence])


def _fragment(rng: random.Random) -> str:
    kind = rng.randrange(13)
    if kind == 0:
        return f"{'#' * rng.randint(1, 3)} {_words(rng, rng.randint(1, 3)).title()}"
    if kind == 1:
        marker = rng.choice(["-", "*", "1."])
        items = []
        for i in range(rng.randint(1, 4)):
            m = f"{i + 1}." if marker == "1." else marker
            items.append(f"{m} {_prose(rng)}")
            if rng.random() < 0.3:
                items.append(f"  - {_words(rng, 3)}")
        return "\n".join(items)
    if kind == 2:
        cols = rng.randint(2, 4)
        header = "| " + " | ".join(_words(rng, 1).title() for _ in range(cols)) + " |"
        sep = "|" + "|".join("---" for _ in range(cols)) + "|"
        rows = ["| " + " | ".join(rng.choice([_words(rng, 1), f"**{_words(rng, 1)}**", "4", "$10"])
                                  for _ in range(cols)) + " |" for _ in range(rng.randint(1, 4))]
        return "\n".join([header, sep, *rows])
    if kind == 3:
        return _code(rng)
    if kind == 4:
        return "    " + f"print('{rng.choice(EMOJI)} **x**')"
    if kind == 5:
        return f"$$\n\\text{{**{rng.choice(WORDS)}**}} {rng.choice(EMOJI)}\n$$"
    if kind == 6:
        return "> " + _prose(rng)
    if kind == 7:
        return rng.choice(["---", "***", "___"])
    if kind == 8:
        return rng.choice(RTL) + " " + _words(rng, 2)
    if kind == 9:
        return BRAILLE
    if kind == 10:
        return "\n".join(TREE)
    if kind == 11:
        return f"{rng.choice(EMOJI)} {_words(rng, 3)}"
    return _prose(rng)


def reply(seed: int) -> str:
    rng = random.Random(seed)
    return "\n\n".join(_fragment(rng) for _ in range(rng.randint(1, 8)))


SOUP = ("*_~`#>|-+=[]()<>!$\\:. \n\t" + "abcxyz" + "".join(EMOJI) + "مرحباשלום" + "⠓⠑━│└"
        + "\u0301\u200d\ufe0f" + "日本語")


def soup(seed: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice(SOUP) for _ in range(rng.randint(0, 400)))
