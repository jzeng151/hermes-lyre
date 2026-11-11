# 0002. Core pipeline edge cases

Status: Accepted
Issue: #3

## Context

Building the core pipeline (processing steps 1 to 7 of the formatter spec) surfaced cases the spec does not settle. Each choice below favours leaving the reply alone over guessing, because the rewrite is stored and the model reads it later.

## Decision

1. **Line endings.** All-LF and all-CRLF replies are formatted; a changed CRLF reply comes back with CRLF. A reply that mixes CRLF with bare LF, or has a bare CR, is returned unchanged. The spec asks for unchanged lines to keep their own endings and changed lines to use the dominant one; tracking per-line endings through rules that add and remove lines is complex for a case that barely occurs in model output.
2. **Placeholder collision.** Protected spans become tokens built from the private-use characters U+E000 and U+E001. A reply that already contains either is returned unchanged, so a token can never be confused with reply text.
3. **Guard scope for block rules.** When a block rule returns the same number of lines it received, the exposed-syntax guard (step 6) restores individual lines. When the count changes, lines cannot be paired with their sources, so any newly exposed syntax restores the whole block. This is conservative and still idempotent: the second pass reaches the same decision.
4. **Blank lines after a removal.** When a rule removes a whole block, the blank lines around it collapse to at most one blank line that was already there, none at the start or end of the reply. No blank line is ever added, and blank runs away from a removal are left alone.
5. **Span order.** Link targets are protected before bare URLs, so a URL inside `[label](url)` is stashed once with its exact boundaries. The spec lists bare URLs first; the result is the same text, protected once.
6. **Inline rule contract.** An inline rule that returns a newline is treated as a failure, and the whole reply is returned unchanged. A line an inline rule empties is dropped, unless it was already blank.

## Consequences

- Every uncertain case leaves the reply as written, so information is never lost and the second pass always matches the first.
- Cost: replies with mixed line endings get no cleanup at all, and a block rule that changes line counts loses its whole rewrite when one line would expose block syntax. Both are rare and can be refined with evidence from the golden corpus (#15).
