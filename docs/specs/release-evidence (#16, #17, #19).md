# Evidence Log: Release

Spec: [DESIGN.md](../../DESIGN.md), [speech-formatter](speech-formatter/spec%20%28%233-%239%29.md), [reply-rewrite-hook](reply-rewrite-hook%20%28%2310%29.md), [settings](settings%20%28%2311%29.md), [a11y-command](a11y-command%20%28%2312%29.md)
Issues: #16, #17, #19
Release: first catalog release (pinned commit recorded below)
Owner: @jzeng151

Pinned commit: `________________________________________`
Hermes version tested: v0.23.0

## Go/no-go gate

All three must pass before the catalog PR is opened.

| Criterion | Evidence | Link | Result |
| --- | --- | --- | --- |
| G-1 Clean install on Hermes v0.23.0 | `hermes plugins install` log into a new profile; `hermes plugins doctor --ci` and `hermes plugins validate --install-deps` output | | Pending |
| G-2 Screen-reader before/after | Recording and transcript, same stored reply, same client, voice and speed, Lyre off then on | | Pending |
| G-3 Row-9 follow-up after resume | Session transcript: 9-row table reply, session resumed, question about row 9 answered correctly | | Pending |

## Acceptance Evidence

| Criterion | Evidence | Link | Result |
| --- | --- | --- | --- |
| Hook AC-3 Telegram rewrite | Telegram DM screenshot or export, Lyre on | | Pending |
| Hook AC-3 Classic CLI, streaming off | Terminal transcript | | Pending |
| Hook AC-3 Classic CLI, streaming on | Terminal transcript showing raw then rewrite (documented limit) | | Pending |
| Hook AC-3 TUI | Terminal transcript | | Pending |
| Hook AC-3 Cron | Cron job output delivered with Lyre on; no prompt waited on | | Pending |
| Hook AC-3 Desktop default off | Desktop screenshot of an unchanged reply with Lyre on | | Pending |
| Hook AC-6 Toggle without restart | Transcript: `/a11y off`, next reply unchanged, `/a11y on`, next reply rewritten | | Pending |
| Hook AC-10 Five-turn conversation | Transcript diff Lyre on vs off; no lost cell, URL or code line | | Pending |
| Command AC-8 Persistence across restart | Gateway restart, then `/a11y status` | | Pending |
| Command AC-10 Every surface | `/a11y status` in CLI, TUI, Telegram | | Pending |
| Command Q2 `local` surface | `/a11y on` from Desktop turns on `desktop` | | Pending |
| Settings AC-3, AC-4 Desktop form | Screenshot of the form; change saved and applied | | Pending |
| Safe-worker and out-of-process host | Whether transform hooks run in each; result written into the README limits | | Pending |

## Catalog Evidence

| Rule | Evidence | Link | Result |
| --- | --- | --- | --- |
| 2 Exact SHA | Catalog entry `sha` equals the pinned commit above | | Pending |
| 6 Declared capabilities | `provides_hooks: [transform_llm_output]`; manifest test and validate output | | Pending |
| 7 Install scanner | `hermes plugins validate` security scan result on the pinned commit | | Pending |
| 9 No core overrides | Private-import check in validate; code review note | | Pending |
| 10 Dependencies | Standard library only; no requirements file | | Pending |
| 13 Disclosures | README section link | | Pending |
| 14 `requires_hermes` | `>=0.23.0` in `plugin.yaml` and the catalog entry; tested on v0.23.0 | | Pending |
| Preflight | Community hackathon-judge output | | Pending |

## Operational Evidence

- Hermes log: search for `lyre:` warnings during the live runs; expected none.
- Timing: largest live reply and its formatter time from the `INFO` log, if any exceeded 200 ms.
- Stop signal: G-3 fails, any live reply loses information, or the screen-reader after recording is not clearly better.

## Manual Checks

- [ ] README read end to end with a screen reader.
- [ ] Install command in the README works when copied as written.
- [ ] Transcripts and fixtures in the repo contain no personal data.

## Known Gaps

- Gap: live runs cover the classic CLI, TUI, Telegram, cron and Desktop only; other platforms rely on unit and round-trip tests.
- Risk: a platform adapter not covered by round-trip tests re-renders Lyre output badly.
- Owner: @jzeng151
- Follow-up: README invites reports, with steps to share a scrubbed reply.
