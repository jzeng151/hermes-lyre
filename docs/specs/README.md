# Specs

Design: [DESIGN.md](../../DESIGN.md)

Each spec follows the spec-coding.dev templates: the SDD packet (spec, tasks, evidence) for the formatter, feature and API-style specs for the hook, settings and command, and an evidence log for release.

| Issue | Spec | Template | Status |
| --- | --- | --- | --- |
| #3 to #9 Speech formatter | [speech-formatter/spec.md](speech-formatter/spec%20%28%233-%239%29.md), [tasks.md](speech-formatter/tasks%20%28%233-%239%2C%20%2313%2C%20%2315%29.md), [test-evidence.md](speech-formatter/test-evidence%20%28%233-%239%2C%20%2313-%2315%29.md) | Packet | Review |
| #10 Reply rewrite hook | [reply-rewrite-hook.md](reply-rewrite-hook%20%28%2310%29.md) | Feature + API contract | Review |
| #11 Settings | [settings.md](settings%20%28%2311%29.md) | Feature + API contract | Review |
| #12 `/a11y` command | [a11y-command.md](a11y-command%20%28%2312%29.md) | Feature | Review |
| #13, #14, #15 Formatter verification | [speech-formatter/test-evidence.md](speech-formatter/test-evidence%20%28%233-%239%2C%20%2313-%2315%29.md) and tasks T10 to T13 | Evidence log | Review |
| #16, #17, #19 Live runs, screen-reader gate, catalog | [release-evidence.md](release-evidence%20%28%2316%2C%20%2317%2C%20%2319%29.md) | Evidence log | Review |
| #22 Plain progress (stretch) | [plain-progress.md](plain-progress%20%28%2322%29.md) | Feature + contract | Draft |
| #23 Accessible web chat (stretch) | [accessible-web-chat.md](accessible-web-chat%20%28%2323%29.md) | Feature + API contract | Draft |

## Issues without a spec

- #1 Scaffold: setup work, done in its own session; the design doc's layout follows it.
- #2 Baseline test: an investigation. Its result closes Q1 and Q2 in the formatter spec.
- #18 README, #20 demo video, #21 user invitations: writing and outreach; requirements are in the issues.
- #24 `write-for-ears` skill: content only, no behavior to specify.
- #25 to #28 Future work: blocked on capabilities plugins lack; each issue records what would unblock it.

## Open questions across specs

| Spec | Question | Resolved by |
| --- | --- | --- |
| speech-formatter | Q1 Code-fence rule per profile | #2 |
| speech-formatter | Q2 Lists on markdown clients | #2, #13 |
| speech-formatter | Q3 Markdown platform list | #13 |
| speech-formatter | Q4 Table pass-through limits | #15 |
| a11y-command | Q2 Surface for `local` commands | #16 |
| plain-progress | Q1 to Q3 | Before starting #22 |
| accessible-web-chat | Q1 to Q4 | Before starting #23 |
