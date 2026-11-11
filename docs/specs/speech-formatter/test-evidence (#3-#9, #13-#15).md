# Evidence Log: Speech Formatter

Spec: [spec.md](spec%20%28%233-%239%29.md)
Release: first catalog release
Owner: @jzeng151

## Acceptance Evidence

| Criterion | Evidence | Link | Result |
| --- | --- | --- | --- |
| AC-1 9-row table keeps every cell | Unit test `test_tables.py::test_nine_rows` | | Pending |
| AC-2 Malformed table byte-identical | Unit tests per pass-through condition | | Pending |
| AC-3 Long signed URL byte-identical | Unit test, both profiles | | Pending |
| AC-4 Emoji-only reply | Unit test | | Pending |
| AC-5 Idempotent | Property test over golden corpus and fuzz inputs | | Pending |
| AC-6 Code contents byte-identical | Property test | | Pending |
| AC-7 Protected spans unchanged | Unit tests | | Pending |
| AC-8 Oversize input skipped | Unit and timing test | `test_core.py::test_oversize_input_is_the_same_object_and_fast` | Pass |
| AC-9 Under 50 ms for 20 KB | Performance test on CI | | Pending |
| AC-10 No spoken markup in transformed regions | Property test with the pass-through exemptions | | Pending |
| AC-11 No English inserted in non-Latin replies | Unit tests (Japanese, Arabic, Russian samples) | | Pending |
| AC-12 Verbosity keeps all information | Parametrized test | | Pending |
| AC-13 Exception returns input | Unit test with a rule forced to raise | `test_core.py::test_raising_rule_returns_input` | Pass |
| AC-14 Survives core WhatsApp plain-output formatter | Round-trip test | | Pending |
| AC-15 Escapes and inline code stable across passes | Unit test, plain profile | | Pending |
| AC-16 Braille text unchanged | Unit test | | Pending |
| AC-17 Display math byte-identical | Unit test, both profiles | | Pending |
| AC-18 Deep lists stay idempotent | Unit test, two passes | | Pending |
| AC-19 Emoji-only reply returned unchanged | Unit test | | Pending |
| AC-20 Unfenced tree lines unchanged | Unit test, two passes | | Pending |
| AC-21 Indented code labeled once, kept byte-identical, also inside lists | Unit test, two passes | | Pending |
| AC-22 No block syntax exposed by inline rewrites | Unit test, two passes | | Pending |
| AC-23 Code inside blockquotes protected | Unit test, both profiles, two passes | | Pending |

## Operational Evidence

- CI run: pytest summary and the commit SHA it ran on.
- Golden corpus: number of fixtures, number of `plain` and `markdown` expected outputs.
- Fuzz: number of generated cases per run and the seed range.
- Performance: median and worst time for the 20 KB fixture.
- Stop signal: any change to code or URL bytes in a golden diff; any idempotency failure.

## Manual Checks

- [ ] Read five golden outputs aloud with a screen reader and note anything that sounds wrong.
- [ ] Review the round-trip outputs for each adapter by eye.
- [ ] Confirm the fence decision from #2 is reflected in R7 and its tests.
- [ ] Confirm the backtick and backslash finding from #2 (Q5) is reflected in R1, R8 and their tests.

## Known Gaps

- Gap: platforms other than Telegram, Discord, Slack and WhatsApp are covered by unit tests only, not adapter round trips.
- Risk: an unlisted adapter re-renders Lyre output in a way that is spoken as symbols.
- Owner: @jzeng151
- Follow-up: add round-trip fixtures when a user reports a platform.
