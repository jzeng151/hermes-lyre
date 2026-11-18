# 0011. Drop the backslash from prose escapes that cannot become markup

Status: Accepted
Issue: #51

## Context

TalkBack reads every backslash that reaches the screen. The Telegram baseline (`docs/baseline/telegram-talkback.md`, probe `docs/baseline/probe-escapes.md`) showed that a Markdown escape in prose, such as `retry\*limit` or `2 \* 3`, is displayed with its backslash, so a TalkBack listener hears "backslash" each time. NVDA skips backslashes at its default punctuation level. ADR 0007 kept every escape as written for the time being.

Lyre protects each backslash escape as a span (spec step 2). Removing a backslash is only safe when the bare character cannot become markup on the next pass, or in the app that displays the reply. Running the escapes and their bare forms through the Hermes adapters showed:

- Telegram's MarkdownV2 conversion escapes the backslash itself, so `2 \* 3` is displayed as `2 \* 3`. A bare `2 * 3` is escaped by the adapter and displayed as `2 * 3`.
- WhatsApp, Slack and the plain profile's clients pass the backslash through, and it is displayed.
- Discord renders the escape, so the backslash is already hidden there; the bare character displays the same.
- Core's plain-text formatter (SMS, iMessage) pairs `*` characters across lines and ignores backslashes: it drops any two in the same message, so `2 \* 3 = 6` and `4 \* 5 = 20` on two lines become `2 \ 3 = 6` and `4 \ 5 = 20` without Lyre, and `2  3 = 6` and `4  5 = 20` with it. A lone `*` in the message survives.
- Telegram's adapter in Hermes v0.23.0, the plugin's minimum version, ignores both flanking and backslashes. It turns any two `*` on one line into italics, so in `2 * 3 = 6 and retry\*limit` the text between the two asterisks is shown in italics. Later versions escape the bare characters instead. No messaging adapter in either version (Telegram, WhatsApp, Discord, Slack) pairs `*`, `_` or `~` across lines; only core's plain-text formatter does.

## Decision

A new inline rule, R10, runs last on both profiles. It replaces an escape placeholder with its bare character only when the character stands alone between two words: a space or tab directly on each side, and a letter or digit as the nearest character past that whitespace on each side.

- Whitespace on both sides makes `*`, `_` and `~` neither left- nor right-flanking, so they cannot open or close emphasis or strikethrough, in Lyre's R1 or in CommonMark, Telegram, WhatsApp, Slack or Discord.
- A word before the character rules out every line-start construct (heading, list item, quote, rule, Setext underline), including inside list items and table cells. A word after it rules out a heading's closing `#` run and keeps neighbouring escapes and protected spans out of the decision.
- `` ` ``, `[`, `]`, `|`, `$` and `\` always keep their backslash: a bare backtick can pair into a code span, a bracket can start a link, a pipe can split a table row, a dollar sign can open math in some apps, and removing one backslash of `\\` still leaves one to hear.
- Escapes inside a word (`retry\*limit`), paired escapes (`\_name\_`) and escapes at the start of a line or container keep their backslash. They could form markup on a second pass, possibly across lines in a client's Markdown parser, which Lyre's per-line rules cannot see.
- The rule runs after every other inline rule, so the words it checks are the ones in the output and a second pass makes the same decision. Code, math, URLs, link destinations and HTML tags are protected before it runs and are never changed.
- `*`, `_` and `~` lose their backslash only when the escape is the only one of that character on its line. Bare copies, other escapes and copies inside protected text (code spans, URLs, link destinations) all count. Otherwise every escape of that character on the line stays, so Lyre never gives such an app a pair it would not have had in the reply as written. Counting per line, not per paragraph, matches what the messaging adapters do and still removes the backslash in the common one-operator line. A second pass sees the same line and makes the same decision.
- The line that counts is the output line. R6 speaks a table row as one line that joins the column names and every cell, while the other inline rules see one cell at a time. So R6 runs R10 on each spoken line it builds (the header sentence, each `Row N:` sentence and each `Columns:` reminder), never on a single cell. `| 2 \* 3 | 4 \* 5 |` keeps both backslashes, and `| 2 \* 3 | x |` loses one. The same holds for an escape at the start of a cell (`\# 1`): in the spoken row a column name precedes it. Other places that build a line from separately processed text either keep each piece on its own line (code labels, the `Quote:` line, list items) or run the inline rules on the joined text (Setext heading lines, link text).
- One rule for both profiles: on every surface checked, the bare character displays the same as or better than the escape.

## Consequences

- TalkBack users no longer hear "backslash" for arithmetic and other spaced symbols in prose (`2 * 3`, `10 - 4`, `x # 1`).
- A line with two products (`2 \* 3 and 4 \* 5`), or an operator next to `retry\*limit` or a URL containing `*`, is still read with its backslashes.
- In-word and paired escapes such as `retry\*limit` and `\_name\_` are still read with their backslash. Removing those safely needs paragraph-wide pairing checks, which this decision does not attempt.
- On SMS and iMessage, core's plain-text formatter still drops two asterisks anywhere in a message, on one line or across lines. Lyre cannot prevent that, and the result is no worse than before (the backslashes used to be left behind on their own).
- On Telegram with Hermes v0.23.0, a spoken table row with two `*` from different cells is shown in italics even when both keep their backslashes, because that adapter ignores backslashes. This comes from R6 joining cells; R10 neither causes it nor makes it worse.
- Two existing idempotence gaps reach a few more inputs, because any changed line can expose them: a changed paragraph line directly above a line indented by four or more columns gains a blank line, and list output can change how an unmatched backtick pairs across lines. Both already happen with emphasis and strikethrough; fixing them is separate work in the core pipeline.
- The TalkBack re-listen on Telegram with `docs/baseline/probe-escapes.md` is a manual check that remains to be done.
