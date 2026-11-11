# 0004. Match emoji by presentation, not by Unicode block

Status: Accepted
Issue: #5

## Context

R4 first matched every character in U+2600 to U+27BF and U+1F000 to U+1FAFF, the same ranges as core's opt-in WhatsApp plain-output formatter. Those blocks also hold symbols that carry meaning in text: music sharps and flats (`F♯`, `B♭`), stars, check marks, chess pieces, alchemical and arrow signs. Removing them as decoration deletes information the model and the listener need. The ranges also missed emoji outside them (`◽`, `◾`, `Ⓜ️`).

## Decision

Match emoji by how they display, following the Unicode emoji data:

- Characters that display as emoji by default always count (pictographs, `◽`, `⭐`, `✨` and the rest).
- Characters that are text by default (`©`, `↔`, `❤`, `☀`, `Ⓜ`) count only when followed by the emoji presentation selector U+FE0F.
- Inside a zero-width-joiner sequence, parts may omit the selector, so sequences like the woman health worker or the heart on fire are removed whole.
- The status symbols `✔`, `☑`, `✖` and `⚠` always count, because models often write them without the selector and they carry status.
- Symbols with no emoji presentation (`♯`, `♭`, `★`, `✓`, `♞`, alchemical and arrow signs) are never touched.

The status words still match core's labels, so running both formatters gives one label, not two.

## Consequences

- Music notation, ratings, chess moves and other symbols survive.
- Lyre and core's WhatsApp formatter can differ on text-default symbols without U+FE0F: core removes `❤` alone, Lyre keeps it. Lyre's choice keeps information.
- Cost: the emoji tables are written out by hand from the Unicode emoji data and need a refresh when Unicode adds emoji. Unknown new pictographs in the existing pictograph blocks are still matched.
