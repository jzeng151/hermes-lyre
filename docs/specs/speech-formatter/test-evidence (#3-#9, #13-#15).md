# Evidence Log: Speech Formatter

Spec: [spec.md](spec%20%28%233-%239%29.md)
Release: first catalog release
Owner: @jzeng151

## Acceptance Evidence

| Criterion | Evidence | Link | Result |
| --- | --- | --- | --- |
| AC-1 9-row table keeps every cell | Unit test | `test_tables.py::test_ac1_nine_rows_keep_every_cell_in_order` | Pass |
| AC-2 Malformed table byte-identical | Unit tests per pass-through condition | `test_tables.py::test_ac2_malformed_and_oversized_tables_byte_identical` | Pass |
| AC-3 Long signed URL byte-identical | Unit test, both profiles | `test_links.py::test_ac3_long_signed_url_byte_identical` | Pass |
| AC-4 Emoji-only reply | Unit test | `test_emoji.py::test_words_policy[plain-✅🎉-(done)]` | Pass |
| AC-5 Idempotent | Property and fuzz tests, 150 generated replies and 150 random inputs per profile | `test_properties.py::test_ac5_idempotent`, `test_fuzz.py::test_soup_never_raises_and_is_idempotent` | Pass |
| AC-6 Code contents byte-identical | Property test (code, math and URLs) | `test_properties.py::test_ac6_code_math_and_urls_byte_identical` | Pass |
| AC-7 Protected spans unchanged | Unit tests | | Pending |
| AC-8 Oversize input skipped | Unit and timing test | `test_core.py::test_oversize_input_is_the_same_object_and_fast` | Pass |
| AC-9 Under 100 ms for 20 KB | Performance test on CI | `test_hook.py::test_ac8_twenty_kb_under_100_ms` | Pass |
| AC-10 No spoken markup in transformed regions | Property test with the pass-through exemptions | `test_properties.py::test_ac10_no_spoken_markup_outside_protected_spans` | Pass |
| AC-11 No English inserted in non-Latin replies | Unit tests (Japanese, Arabic, Russian samples) | | Pending |
| AC-12 Verbosity keeps all information | Parametrized test | `test_verbosity.py::test_ac12_every_level_keeps_all_information`, `test_levels_only_change_framing` | Pass |
| AC-13 Exception returns input | Unit test with a rule forced to raise | `test_core.py::test_raising_rule_returns_input` | Pass |
| AC-14 Survives core WhatsApp plain-output formatter | Round-trip test | | Pending |
| AC-15 Escapes and inline code stable across passes | Unit test, plain profile | | Pending |
| AC-16 Braille text unchanged | Unit test | | Pending |
| AC-17 Display math byte-identical | Unit test, both profiles | | Pending |
| AC-18 Deep lists stay idempotent | Unit test, two passes | `test_lists.py::test_ac18_three_levels_with_fence_in_deepest_item` | Pass |
| AC-19 Emoji-only reply returned unchanged | Unit test | | Pending |
| AC-20 Unfenced tree lines unchanged | Unit test, two passes | | Pending |
| AC-21 Indented code labeled once, kept byte-identical, also inside lists | Unit test, two passes | `test_code.py::test_ac21_indented_code_labelled_once_and_byte_identical`, `test_code.py::test_ac21_indented_code_inside_list_item` | Pass |
| AC-22 No block syntax exposed by inline rewrites | Unit test, two passes | | Pending |
| AC-23 Code inside blockquotes protected | Unit test, both profiles, two passes | `test_code.py::test_ac23_code_inside_quote` | Pass |

## Operational Evidence

- CI run: pytest summary and the commit SHA it ran on.
- Golden corpus: number of fixtures, number of `plain` and `markdown` expected outputs.
- Fuzz: number of generated cases per run and the seed range. CI runs seeds 0 to 149 (`LYRE_FUZZ_SEED`, `LYRE_FUZZ_CASES` widen it). A sweep of seeds 150 to 2149 passed every property on generated replies; 7 of 4,000 random-character inputs were not idempotent, listed in #43.
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
