# Architecture decision records

Decisions made while building Lyre, one file per decision, named with the issue it belongs to. Each record says what was decided, why, and what it costs. A record is never edited to reverse a decision; a later record supersedes it.

| ADR | Decision | Issue | Status |
| --- | --- | --- | --- |
| [0001](0001-formatter-signature%20%28%233%29.md) | The formatter takes explicit options, not a platform and a settings map | #3 | Accepted |
| [0002](0002-formatter-core-edge-cases%20%28%233%29.md) | Core pipeline edge cases: line endings, option errors, guard scope, blank lines | #3 | Accepted |
| [0003](0003-guard-scope-and-underscore-emphasis%20%28%234%29.md) | Quotes skip the guard, block rules are guarded whole, underscore emphasis needs a clear end | #4 | Accepted |

Format: Context, Decision, Consequences (after Michael Nygard).
