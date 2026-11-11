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
- No HTML handling. Raw HTML (`<details>`, `<br>`) passes through unchanged.
- No math rendering. `$$...$$` blocks pass through unchanged.
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
- Pure: the same input and arguments always give the same output.

## Processing model

1. **Size gate.** Over the byte cap: return input.
2. **Protect spans.** Fenced code blocks (``` and ~~~, with or without an info string), indented code blocks (4 spaces or a tab, not inside a list item), inline code, bare URLs and link targets are replaced by placeholders. Nothing inside a placeholder is ever modified.
3. **Block pass.** Lines are grouped into blocks: table, list, heading, rule, blockquote, paragraph. One linear pass; no backtracking regexes.
4. **Rules.** Each block is handed to the rule that owns it. Inline rules (emphasis, emoji, links) run on paragraph, list item, heading and table cell text.
5. **Restore spans**, applying the code and link rules to the placeholders' surroundings.
6. **Normalize whitespace** introduced by removals only: no more than one blank line in a row, no trailing spaces on changed lines. Unchanged lines keep their original spacing.

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
| `\*` and other backslash escapes | the literal character |

- Markers are removed only when they pair on the same line. An unpaired `*` or `_` is left as is (for example `2 * 3`, `snake_case`).
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
- A line made only of box-drawing characters (U+2500 to U+257F), block elements (U+2580 to U+259F), braille spinner characters (U+2800 to U+28FF) and spaces is removed.
- Box-drawing characters inside a line of text are replaced by a single space.
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
- Nested lists indent by 2 spaces per level (never 4, which some formatters treat as code).
- Task lists: `- [x] Done` -> `1, (done) Done`; `- [ ] Open` -> `1, (not done) Open`.
- A list item's continuation lines and inline code are kept.
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
- Escaped pipes (`\|`) inside cells are kept as `|` in the cell text and do not split cells.
- Alignment colons in the separator row are ignored.
- A table passes through **byte-identical** if any of these hold:
  - no separator row directly under the header,
  - a body row with more cells than the header,
  - more than 50 body rows,
  - more than 10 columns,
  - any cell over 500 characters.
- A body row with fewer cells than the header is padded with `blank`.
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
- Idempotency: if the line directly before a fence is already a label in Lyre's form and the line after it is `End of code.`, no label is added.
- Indented code blocks get the same labels with `Code, N lines:`; their indentation is kept.
- `brief`: `Code:` before, `End of code.` after.
- `full`: as `normal`.
- Applies to both profiles.

### R8. Inline code and links

| Input | Output |
| --- | --- |
| `` `npm test` `` | `npm test` (plain); unchanged (markdown) |
| `[docs](https://x.test/a?b=1)` | `docs, link: https://x.test/a?b=1` |
| `[https://x.test](https://x.test)` | `https://x.test` |
| `<https://x.test>` | `https://x.test` |
| `![chart](https://x.test/c.png)` | `Image: chart, link: https://x.test/c.png` |
| bare `https://x.test/...` | unchanged |

- URLs are never shortened, decoded or re-encoded.
- Inline code containing a backtick (double-backtick spans) keeps its inner text exactly.
- `markdown` profile: links are still rewritten, because the raw URL is what lets a listener open or copy it; inline code is left to the client.
- `brief` and `full`: no difference.

### R9. Blockquotes

- `> text` -> `text` (the marker is removed; nested `> >` too).
- `full`: the first line of each quote is prefixed `Quote: `.
- Plain only.

## Acceptance Criteria

- [ ] **AC-1** Given a 9-row table with a value only in row 9, when formatted, then every cell value appears in the output in row order.
- [ ] **AC-2** Given a malformed table (no separator row, or an extra cell in a body row), when formatted, then the table lines are byte-identical to the input.
- [ ] **AC-3** Given a reply containing a 600-character signed URL with `%`, `&`, `=` and `_`, when formatted on either profile, then the URL appears byte for byte.
- [ ] **AC-4** Given a reply that is only `✅🎉`, when formatted with `emoji_policy: words`, then the output is `(done)`.
- [ ] **AC-5** Given any input, when formatted twice with the same arguments, then the second output equals the first.
- [ ] **AC-6** Given code blocks containing `**`, `|`, `#` and emoji, when formatted, then the code contents are byte-identical.
- [ ] **AC-7** Given escaped pipes, inline code, indented code and an unclosed fence, when formatted, then those spans are unchanged.
- [ ] **AC-8** Given input over 200,000 bytes, when formatted, then the output is the input object unchanged and the call returns in under 5 ms.
- [ ] **AC-9** Given a 20 KB reply mixing every rule, when formatted, then it finishes in under 50 ms on CI hardware.
- [ ] **AC-10** Given any output outside protected spans, then it contains no `|---` and no emoji (except under `emoji_policy: keep` or `table_style: unchanged`); and on the `plain` profile also no paired `**` and no line starting with `#`.
- [ ] **AC-11** Given a reply that is mostly non-Latin script, when formatted, then no English words are inserted.
- [ ] **AC-12** Given the same reply at `brief`, `normal` and `full`, then all three contain every cell, URL and code line.
- [ ] **AC-13** Given an internal exception in any rule, when formatted, then the input is returned unchanged.
- [ ] **AC-14** Given output from Lyre run through core's WhatsApp plain-output formatter, then code contents and status words are unchanged.

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

## Output / Deliverables

- Code: `lyre/formatter/` package only (see [tasks.md](tasks%20%28%233-%239%2C%20%2313%2C%20%2315%29.md)).
- Tests: unit per rule and verbosity, property, fuzz, golden corpus, adapter round-trip.
- Rollback: the formatter has no state; reverting a rule is a code revert plus a golden-file update.
