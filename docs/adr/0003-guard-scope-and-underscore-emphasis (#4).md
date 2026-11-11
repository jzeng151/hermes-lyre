# 0003. Guard scope for quotes and block rules; underscore emphasis

Status: Accepted (refines decision 3 of ADR 0002)
Issue: #4

## Context

Implementing R1 (emphasis) and R9 (blockquotes) showed two problems.

1. A plain-profile quote holding fenced code (`> ```py`) loses its markers under R9, so its output lines start with a fence. The step-6 guard treated that as newly exposed syntax and restored the fence lines one by one, leaving the quote half-converted and no longer idempotent.
2. CommonMark reads `__init__.py` as bold "init". In a chat reply it is nearly always a file name, and stripping the underscores loses information the model reads later.

## Decision

1. **Quotes are exempt from the guard.** A quote's contents already went through the whole pipeline, guard included, as a container. Dropping the `>` markers only reveals structure that was genuinely there, and the next pass treats it the same way.
2. **Block rule output is guarded all or nothing.** Per-line restoration applies only to the default inline path, where lines map one to one. If any line of a block rule's output exposes syntax, the whole block is restored.
3. **Underscore emphasis needs a clear end.** `_x_` and `__x__` pair only when the opening marker follows whitespace, line start or punctuation other than `.`, and the closing marker is followed by whitespace, line end or `, ; : ! ? )`. Asterisk emphasis is unchanged.

## Consequences

- Quoted code, tables and lists come out of a plain-profile quote unchanged and stable on the next pass.
- `__init__.py`, `_private_.txt` and similar names keep their underscores.
- Cost: `_italic_.` at the end of a sentence keeps its underscores, which a screen reader may speak. Asterisk emphasis, the more common form in model output, is not affected.
