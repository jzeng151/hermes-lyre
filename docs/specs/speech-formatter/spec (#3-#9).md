# Speech Formatter Spec

Issues: #3, #4, #5, #6, #7, #8, #9
Design: [DESIGN.md](../../../DESIGN.md)
Owner: @jzeng151
Status: Review

## Goal

Given a final Hermes reply, return text a screen reader reads cleanly, keeping every piece of information and changing only what a screen reader would speak as noise.

## Non-goals

- No summarizing, shortening or reordering of content.
- No change to code contents, URLs, or any text inside a protected span.
- No currency, number, date or abbreviation expansion. Screen readers already handle these.
- No HTML handling. HTML tags (`<details>`, `<br>`) are protected spans and pass through unchanged; text between tags is prose.
- No math rendering. Display math (`$$...$$`) is a protected span and passes through byte-identical. Single-dollar inline math is not recognized, because `$10` is far more common in replies.
- No translation. Inserted words are English only.
- No I/O, no Hermes imports, no logging inside the formatter.

## Contract

```python
def format_for_speech(
    text: str,
    *,
    profile: Literal["plain", "markdown"],
    verbosity: Literal["brief", "normal", "full"] = "normal",
    emoji_policy: Literal["words", "remove", "keep"] = "words",
    table_style: Literal["sentences", "unchanged"] = "sentences",
) -> str
```

- Returns a string. Never raises: any internal exception returns `text` unchanged.
- Returns `text` unchanged when it is empty, over 200,000 bytes in UTF-8, or fails to parse.
- Returns `text` unchanged when the result would be empty or whitespace-only (for example a reply that is only decorative emoji). The original is a better answer than nothing, and Hermes ignores empty rewrites anyway.
- Pure: the same input and arguments always give the same output.

## Processing model

1. **Size gate.** Over the byte cap: return input.
2. **Protect spans.** In this order: fenced code blocks (``` and ~~~, with or without an info string, at any indentation, so a fence nested in list output is still a fence on the next pass), display math (`$$...$$`, on one line or across lines), indented code blocks (after a blank line: 4 spaces or a tab at the top level, or the list item's content column plus 4 inside a list item), inline code, backslash escapes (`\` followed by an ASCII punctuation character), HTML tags, bare URLs and link targets are replaced by placeholders. Nothing inside a placeholder is ever modified. Lyre's own output never starts a line with 4 or more spaces outside a protected span, so a second pass never finds new indented code.
3. **Block pass.** Lines are grouped into blocks: table, list, heading, rule, blockquote, paragraph. One linear pass; no backtracking regexes. A blockquote is a container: its `>` markers are removed and its contents go through steps 2 to 7 on their own, span protection included, so fenced or indented code inside a quote is protected and `> # Title` is a heading inside the quote. If any quote is nested more than 10 deep, the outermost quote holding it is left unchanged, which keeps the work linear in practice and stays idempotent.
4. **Rules.** Each block is handed to the rule that owns it. Inline rules (emphasis, emoji, links) run on paragraph, list item, heading and table cell text.
5. **Restore spans**, applying the code and link rules to the placeholders' surroundings.
6. **Guard against exposed block syntax.** If any rule, inline or block (heading, quote, table, list), produces an output line that starts, after its indentation, with block syntax the input line it came from did not start with (a list marker `-`, `*`, `+`, `N.` or `N)`; `#`; `>`; `|`; a thematic break; a code fence; or a Setext underline, a line of only `=` or only `-` characters, which is block syntax only because of the non-blank line above it), that line is restored to its input text. Lyre's own fixed forms (`N, item`, count lines, labels, `Row N:`) never start with block syntax, so they are unaffected. Inline rules are guarded line by line; a block rule's output is restored as a whole block if any line exposes syntax. Quote output (R9) is exempt, because its contents already passed through the guard as a container (ADR 0003). Examples: `[- Build](https://x.test)`, `🎉 1. Done`, `**# Title**` and the heading `# - Build` stay as written. The line keeps some noise, but no structure is invented and the second pass sees the same line and makes the same decision. Where the syntax only appears because of the rendered block above (a heading rewritten into a paragraph line over a `===` paragraph, or a table separator under a new line with a pipe), a blank line is inserted between the two blocks, which keeps them as separate as they were in the input.
7. **Normalize whitespace** introduced by removals only: no more than one blank line in a row, no trailing spaces on changed lines. Unchanged lines keep their original spacing.

## Script detection

If fewer than half of the letters outside protected spans are Latin script, the reply is treated as non-English:

- Applied: emphasis markers, horizontal rules, box drawing, decorative emoji removal.
- Not applied: anything that inserts English words (status emoji words, list counts, table sentences, code labels, `link:` labels, `(removed: ...)`). Status emoji are kept as they are.

## Rules

Each rule lists the output at `normal` verbosity, then the differences at `brief` and `full`. "Plain only" means the rule is skipped for the `markdown` profile because the client renders that markup.

### R1. Emphasis (plain only)

| Input | Output |
| --- | --- |
| `**bold**`, `__bold__` | `bold` |
| `*italic*`, `_italic_` | `italic` |
| `***both***` | `both` |
| `~~gone~~` | `(removed: gone)` |
| `\*` and other backslash escapes | unchanged, backslash kept; an escaped character never pairs as a marker |

- Backslash escapes stay as written. Turning `\*literal\*` into `*literal*` would let a second pass strip those asterisks, breaking AC-5. The one exception is `\|` inside a table that R6 converts, because the converted output is never a table again.
- Markers are removed only when they pair on the same line. An unpaired `*` or `_` is left as is (for example `2 * 3`, `snake_case`).
- Underscore markers pair only when the closing marker is followed by whitespace, line end or `, ; : ! ? )`, so `__init__.py` keeps its underscores (ADR 0003).
- Single asterisks may pair inside a word (`un*believ*able`, CJK text) but never next to a digit, so `2*3*4` keeps its operators.
- `brief`: strikethrough becomes `(removed: gone)` as well; no difference.
- `full`: no difference.
- `markdown` profile: strikethrough still becomes `(removed: gone)`, because several clients render it as plain text and the meaning is easy to miss.

### R2. Headings (plain only)

| Input | Output |
| --- | --- |
| `# Results` | `Results.` on its own line, with a blank line before it |
| `## Done!` | `Done!` (no period added after `.`, `!`, `?`, `:`) |
| Setext heading (`Results` + `===` line) | `Results.` |

- `brief`: no difference.
- `full`: `Heading: Results.` for level 1 and 2, `Subheading: Results.` for level 3 and deeper.

### R3. Rules, box drawing and decoration

- A line that is only `---`, `***`, `___` (thematic break) becomes a blank line.
- A line made only of box-drawing characters (U+2500 to U+257F), block elements (U+2580 to U+259F) and spaces is removed.
- A line that mixes box-drawing characters with text (unfenced tree output such as `│   ├── src/`) is left unchanged. Replacing the characters with spaces would indent the line 4 or more spaces, which a second pass reads as code; dropping them would lose the nesting. Whether screen readers speak them is Q6.
- Braille Patterns (U+2800 to U+28FF) are never removed or changed. Terminal spinners use them, but so does real Braille text, and the two cannot be told apart; spinners rarely appear in a final reply.
- Applies to both profiles. Never inside protected spans.

### R4. Emoji

`emoji_policy: words` (default):

| Emoji | Output |
| --- | --- |
| ✅ ✔️ ☑️ | `(done)` |
| ❌ ✖️ 🚫 | `(failed)` |
| ⚠️ | `(warning)` |
| 🔴 | `(red)` |
| 🟡 | `(yellow)` |
| 🟢 | `(green)` |
| ⏳ | `(pending)` |
| any other emoji | removed |

- Whole sequences are one emoji: variation selectors (U+FE0E, U+FE0F), skin tones (U+1F3FB to U+1F3FF), zero-width joiner sequences, keycaps, tag flags. No orphan code point is left behind.
- An emoji is a character that displays as emoji by default, or a text-default character followed by U+FE0F, or a status symbol from the table. Symbols that share Unicode blocks with emoji but have no emoji presentation (`♯`, `♭`, `★`, `✓`) are never removed (ADR 0004).
- Spacing next to emphasis: an emphasis delimiter touching the emoji stays touching the text (`**✅ Done**` -> `**(done) Done**`).
- A run of emoji becomes its status words joined by single spaces: `✅ 🎉 ⚠️` -> `(done) (warning)`.
- Spacing is normalized only where an emoji was removed: `Hello 🎉 world` -> `Hello world`.
- A line that becomes empty after removal is removed.
- `emoji_policy: remove`: all emoji removed, status emoji included.
- `emoji_policy: keep`: rule skipped.
- `brief` and `full`: no difference.
- The words match core's opt-in WhatsApp plain-output formatter, so running both gives one label, not two.

### R5. Lists

Input:

```
- Build
- Test
  - unit
  - live
- Ship
```

Output (`normal`):

```
3 items.
1, Build
2, Test
  2 sub-items.
  sub-item 1, unit
  sub-item 2, live
3, Ship
```

- Ordered lists keep their source numbers: `5. Five` -> `5, Five`.
- Numbers are followed by a comma, never a period, so markdown clients do not turn the output back into a list.
- Nesting is spoken, not shown by depth of indentation: every nested line is indented exactly 2 spaces whatever its level, because 4 spaces would be read as indented code on the next pass and by markdown clients. Level 2 items are `sub-item N`; level 3 and deeper are `level 3 item N` (and `2 level 3 items.` for the count line).
- A list item's prose continuation lines are re-indented to the item's own output indent (0 or 2 spaces). Fenced and indented code inside an item are protected spans: their lines keep their original bytes, including indentation, and get R7 labels at the item's output indent.
- An item that is only a code block (a fence opened on the item line, `- ```py`) puts its number on its own line (`1,`) and the code on the next line, so the fence starts a line and stays protected on the next pass.
- Task lists: `- [x] Done` -> `1, (done) Done`; `- [ ] Open` -> `1, (not done) Open`. A task box needs a space or the item end after `]`, so a link labelled `x` is not a task.
- A change of marker type at the same level (`-` to `1.`, `-` to `*`) starts a separate list with its own count.
- Prose after a nested list belongs to the item whose content column it reaches.
- An item emptied by the inline rules (only decoration) keeps its number and nothing else.
- A list whose item continuation lines hold a heading, quote, thematic break or table is left to the default inline handling, because speaking it would change what the next pass sees.
- A list item's inline code is kept.
- A single-item list still gets `1 item.`.
- `brief`: no count lines.
- `full`: count lines say `List, 3 items.` and `Sub-list, 2 items.`; the list ends with `End of list.`.
- Applies to both profiles.

### R6. Tables

Input:

```
| Name  | Price | Stock |
|-------|------:|-------|
| Alpha | $10   | 4     |
| Beta  | $12   |       |
```

Output (`normal`, `table_style: sentences`):

```
Table, 2 rows, 3 columns: Name, Price, Stock.
Row 1: Name Alpha, Price $10, Stock 4.
Row 2: Name Beta, Price $12, Stock blank.
End of table.
```

- Every cell is kept. Empty cells are spoken as `blank`.
- Cell text gets inline rules (R1, R4, R8). Inline code and URLs in cells are protected.
- Escaped pipes (`\|`) inside cells do not split cells and become `|` in the cell text (the R1 exception).
- Alignment colons in the separator row are ignored.
- A table passes through **byte-identical** if any of these hold:
  - no separator row directly under the header,
  - a body row with more cells than the header,
  - more than 50 body rows,
  - more than 10 columns,
  - any cell over 500 characters (measured as written, protected spans included),
  - joining the cells into sentences would pair emphasis markers that sat in different cells (`*alpha | beta*`).
- A body row with fewer cells than the header is padded with `blank`. A blank header cell is named `Column N`.
- Tables in mostly non-Latin replies pass through byte-identical, because every sentence form inserts English words.
- `brief`: `Table, 2 rows: Name, Price, Stock.` then `Row 1: Alpha, $10, 4.`; no `End of table.`
- `full`: as `normal`, plus `Columns: Name, Price, Stock.` repeated before every 10th row.
- `table_style: unchanged`: rule skipped.
- Applies to both profiles.

### R7. Code blocks

Input:

````
```python
print("✅ **done**")
```
````

Output (`normal`):

````
Python code, 1 line:
```python
print("✅ **done**")
```
End of code.
````

- Code contents are byte-identical, including trailing spaces and blank lines.
- Label comes from the fence info string, capitalized for known languages (Python, JavaScript, TypeScript, Bash, Shell, JSON, YAML, SQL, Rust, Go, Java, C, C++, C#, Ruby, PHP, HTML, CSS, Markdown, Diff). Unknown or missing: `Code, 12 lines:`.
- Line count is the number of content lines. `1 line`, otherwise `N lines`.
- Fence handling: **open question Q1**. Until #2 decides, fences are kept on every profile.
- Unclosed fence: the rest of the reply is treated as code and left unchanged, with no labels added.
- Indented code blocks get the same labels with `Code, N lines:`; their indentation is kept. A blank line separates each label from an indented block, because a label line directly above it would make markdown read the code as part of the paragraph.
- Idempotency, for fenced and indented blocks alike: if the nearest non-blank line before the block is already a label in Lyre's form and the nearest non-blank line after it is `End of code.`, no label is added.
- `brief`: `Code:` before, `End of code.` after.
- `full`: as `normal`.
- Applies to both profiles.

### R8. Inline code and links

| Input | Output |
| --- | --- |
| `` `npm test` `` | unchanged, backticks kept (both profiles) |
| `[docs](https://x.test/a?b=1)` | `docs, link: https://x.test/a?b=1` |
| `[https://x.test](https://x.test)` | `https://x.test` |
| `<https://x.test>` | `https://x.test` |
| `![chart](https://x.test/c.png)` | `Image: chart, link: https://x.test/c.png` |
| bare `https://x.test/...` | unchanged |

- URLs are never shortened, decoded or re-encoded.
- Inline code keeps its backticks on both profiles. The backticks are the protection boundary: without them, a second pass would treat `**literal**` or a status emoji inside the code as prose and change it, breaking AC-5 and AC-6. Whether screen readers announce the backticks is Q5.
- Inline code containing a backtick (double-backtick spans) keeps its delimiters and inner text exactly.
- `markdown` profile: links are still rewritten, because the raw URL is what lets a listener open or copy it.
- `brief` and `full`: no difference.

### R9. Blockquotes

- `> text` -> `text` (the marker is removed; nested `> >` too). The contents are processed as a container (processing step 3) on both profiles; on the `markdown` profile the markers are then put back on every output line of the quote, so only the quote's contents change.
- `full`: a `Quote:` line before the quote's contents and an `End of quote.` line after them (plain profile only). The announcement is on its own line, never prefixed to the first line, so labels inside the quote (such as an R7 code label) stay recognizable on the next pass.
- Removing the markers is plain only; container processing of the contents runs on both profiles.
- The markers stay (the contents are still processed) when the quote's processed contents hold an unclosed fence, an unclosed `$$` or a list marker, because removing them would change how the rest of the reply parses.
- When text sits directly above the quote, the unwrapped contents start after a blank line, so they stay a separate block on the next pass (a quoted indented code block stays code). The quote's contents keep their own spacing; only the outer pass trims nothing inside them.

## Acceptance Criteria

- [ ] **AC-1** Given a 9-row table with a value only in row 9, when formatted, then every cell value appears in the output in row order.
- [ ] **AC-2** Given a malformed table (no separator row, or an extra cell in a body row), when formatted, then the table lines are byte-identical to the input.
- [ ] **AC-3** Given a reply containing a 600-character signed URL with `%`, `&`, `=` and `_`, when formatted on either profile, then the URL appears byte for byte.
- [ ] **AC-4** Given a reply that is only `✅🎉`, when formatted with `emoji_policy: words`, then the output is `(done)`.
- [ ] **AC-5** Given any input, when formatted twice with the same arguments, then the second output equals the first.
- [ ] **AC-6** Given code blocks containing `**`, `|`, `#` and emoji, when formatted, then the code contents are byte-identical.
- [ ] **AC-7** Given escaped pipes outside tables, backslash escapes, inline code, indented code and an unclosed fence, when formatted, then those spans are unchanged.
- [ ] **AC-8** Given input over 200,000 bytes, when formatted, then the output is the input object unchanged and the call returns in under 5 ms.
- [ ] **AC-9** Given a 20 KB reply mixing every rule, when formatted, then it finishes in under 50 ms on CI hardware.
- [ ] **AC-10** Given a mostly Latin-script reply that the formatter transformed (not returned unchanged under AC-8 or AC-13), then in every transformed region the output contains no `|---` and no emoji (unless `emoji_policy: keep`); and on the `plain` profile also no paired `**` and no line starting with `#`. Transformed regions exclude protected spans and tables passed through under AC-2 or `table_style: unchanged`. Non-Latin replies are exempt from the emoji clause, because Script detection keeps their status emoji.
- [ ] **AC-11** Given a reply that is mostly non-Latin script, when formatted, then no English words are inserted.
- [ ] **AC-12** Given the same reply at `brief`, `normal` and `full`, then all three contain every cell, URL and code line.
- [ ] **AC-13** Given an internal exception in any rule, when formatted, then the input is returned unchanged.
- [ ] **AC-14** Given output from Lyre run through core's WhatsApp plain-output formatter, then code contents and status words are unchanged.
- [ ] **AC-15** Given `\*literal\*` and `` `**literal**` `` in prose, when formatted twice on the `plain` profile, then both are unchanged after each pass.
- [ ] **AC-16** Given a line of Braille Patterns such as `⠓⠑⠇⠇⠕`, alone or inside prose, when formatted, then it is unchanged.
- [ ] **AC-17** Given display math containing `\text{**literal**}` and an emoji, when formatted on either profile, then the `$$...$$` block is byte-identical.
- [ ] **AC-18** Given a list nested three levels deep with a fenced code block in a level 3 item, when formatted twice, then the output is identical, no line outside the fence starts with 4 or more spaces, and no code labels are added on the second pass.
- [ ] **AC-19** Given a reply that is only `🎉`, or only decorative emoji and whitespace, then the output is the input unchanged.
- [ ] **AC-20** Given unfenced tree output with box-drawing characters, when formatted twice, then those lines are unchanged.
- [ ] **AC-21** Given a top-level indented code block and a list item containing indented code (`- Example:`, a blank line, then six-space-indented Python with `**` and an emoji in a string), when formatted twice, then each block's lines are byte-identical, each has exactly one label pair, and the output equals the first pass.
- [ ] **AC-22** Given lines starting with `[- Build](https://x.test)`, `🎉 1. Done`, `**# Title**`, the heading `# - Build`, the two lines `Title` and `**===**`, and `> # Quoted title`, when formatted twice on the `plain` profile at every verbosity, then all but the quote are unchanged (no Setext heading appears), the quote becomes a heading inside the quote, no list, heading or quote structure appears that the input did not have, and the second pass equals the first.
- [ ] **AC-23** Given a blockquote holding an indented code block (`>`, then `>     print("✅ **done**")`) and a fenced block (`> ```py` ... `> ````), when formatted twice on either profile, then the code lines after the quote markers are byte-identical, each block has one label pair, and the second pass equals the first. The same holds at `full` verbosity on the `plain` profile when the quote starts with a fenced block.

## Edge Cases

- **Empty or whitespace-only input:** returned unchanged.
- **Only a table, only code, only emoji, only a URL:** each handled by its rule with no surrounding text added beyond the rule's labels.
- **Duplicates and idempotency:** Lyre's own output contains no markup that triggers a rule again (no pipes, no list markers, no paired `*`, labels recognized before fences).
- **Mixed nesting:** code inside list items, links inside bold, emoji inside table cells, lists inside blockquotes.
- **Right-to-left text:** passes through; inserted words are not placed inside RTL runs.
- **CRLF line endings:** preserved on unchanged lines; changed lines use the input's dominant line ending.
- **Unicode:** combining marks, ZWJ sequences, lone surrogates in input do not raise.
- **Concurrency:** none; pure function.
- **Permissions:** none; no I/O.

## Open Questions

- [ ] **Q1** Code fences: keep everywhere, or strip on plain clients (SMS, Signal, iMessage) and keep on clients that render them (including WhatsApp)? Decided by the baseline test in #2.
- [ ] **Q2** Do Telegram, Discord and Slack screen readers announce rendered lists usefully enough that R5 should be skipped on the `markdown` profile? Decided by #2 and #13.
- [ ] **Q3** Is the `markdown` platform list in the design doc correct for Teams, Mattermost and Google Chat? Checked against each adapter's `format_message` in #13.
- [ ] **Q4** Are the table pass-through limits (50 rows, 10 columns, 500 characters) right? Tuned with the golden corpus in #15.
- [ ] **Q5** Do VoiceOver and NVDA at their default punctuation levels announce the backticks around inline code or the backslash in escapes? If they do, choose another boundary that a second pass can recognize, and update R1, R8, AC-5, AC-6 and AC-15 together. Decided by the baseline test in #2.
- [ ] **Q6** Do VoiceOver and NVDA speak box-drawing characters in unfenced tree lines? If they do, find a representation that keeps nesting and stays idempotent. Decided by the baseline test in #2.

## Output / Deliverables

- Code: `lyre/formatter/` package only (see [tasks.md](tasks%20%28%233-%239%2C%20%2313%2C%20%2315%29.md)).
- Tests: unit per rule and verbosity, property, fuzz, golden corpus, adapter round-trip.
- Rollback: the formatter has no state; reverting a rule is a code revert plus a golden-file update.
