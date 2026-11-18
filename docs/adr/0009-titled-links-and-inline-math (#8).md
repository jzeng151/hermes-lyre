# 0009. Titled links and inline math are left as written

Status: Accepted
Issue: #8

## Context

Two inputs lost information on the way to speech.

- **Link titles.** `[policy](https://example.test "Do not share externally")` became `policy, link: https://example.test`. The title was dropped, and a title is sometimes the only place a reply puts a caveat. Spoken output has no natural place for it: appending it changes the sentence, and dropping it loses meaning.
- **Inline math.** Only `$$...$$` was protected. On the `plain` profile, `$a*b*c$` became `$abc$` and `\(a*b*c\)` became `\(abc\)`, because emphasis stripping treated the `*` as markup. Single-dollar math was left unrecognized on purpose, since `$10` is far more common in replies than math, and a careless rule would read `$5 and *really* $10` as math and leave the asterisks in.

## Decision

- **A link or image whose target has a title is left exactly as written**, label and target included, on both profiles. A title is `"..."`, `'...'` or `(...)` after the destination, as in CommonMark; any other text after the destination counts too, because Lyre cannot tell what the reply meant. Span protection stashes the whole construct (`[label](target)`, `![alt](target)`, or a linked image `[![alt](src)](href)` when either target has a title), so no rule changes it. The link rule also checks for a title and keeps such a link, in case a target reaches it some other way. Untitled links are rewritten as before.
- **A reference definition keeps its title.** In `[r]: https://x.test/a "title"`, the destination and a title on the same line are protected together, so emphasis-shaped text in the title is not stripped.
- **Inline math on one line is a protected span**, in these forms:
  - `$$...$$` (as before);
  - `\(...\)`;
  - `\[...\]` on one line. A backslash-bracket pair could also be two escaped brackets around ordinary text, but replies that escape brackets are rare, and protecting text only means leaving it as written, so the cost of a false match is a few unstripped markers;
  - tight `$...$`, with Pandoc's `tex_math_dollars` rule: the opening `$` is followed by a non-space character, the closing `$` follows a non-space character and is not followed by a digit, and there is no line break inside. The body never holds a `$`, escaped or not, so `$a\$b$` is not math and stays prose. `$5 and *really* $10`, `$5-$10`, `$5/$10` and `costs $3.50, about $4` are therefore not math, and their emphasis is still removed.
- An escaped opener (`\$`, `\\(`) never starts math; the search then tries the next character, so a second pass finds the same math as the first.
- A `\(...\)` body never contains `\(` or `\)`, and a `\[...\]` body never contains `\[` or `\]`, even after another backslash.
- Math never reaches into a link destination or a bare URL; those are protected whole instead.
- Code spans win over `$...$`, `\(...\)` and `\[...\]`: backticks pair first, as they did before. Only `$$...$$` keeps its earlier rule that a backtick inside math opened outside any code span is literal.

## Consequences

- A titled link is read with its markdown punctuation (brackets, parentheses, quotes) and its title. That is noisier than `label, link: URL`, but nothing is lost. Emphasis around the link is still removed.
- Text that matches the dollar rule without being math keeps its markers, for example `$HOME/*$USER` with emphasis-shaped characters inside. Leaving text as written is the safe failure.
- Still not protected: a reference definition's title on the line after its destination; single-dollar math whose body holds an escaped dollar (`$a\$b$`); math across lines with `\[ ... \]` or `\( ... \)` (only `$$` blocks are protected across lines), `\begin{...}` environments outside `$$`, and single-dollar math with a space after the opener or before the closer (`$ x $`), which Pandoc does not read as math either.
- A link label with nested brackets (`[a [b] c](u "t")`) is not recognized as one link; its target is still protected, so the title is kept, but emphasis in the label may be removed.
- Letters inside titled links and math no longer count toward script detection, like letters in other protected spans.
- Lines with a `$` pair or `\(` now go through inline protection, which costs one regex search per such line. The search is linear in the line length. Each position is tried as a start at most once, including after a rejected match, which resumes one character later. No body can pass the next opener or closer of its kind: a `$` for dollar math, `\(` or `\)` for parentheses, `\[` or `\]` for brackets. So the scans of two candidates of the same kind never overlap. `test_performance.py` checks that lines of thousands of escaped dollars, unclosed or escaped `\(` and `\[`, or matches rejected because they reach into a destination or URL scale linearly. It also checks that a 17.6 KB line of escaped prices stays within the 20 KB budget (ADR 0006).
