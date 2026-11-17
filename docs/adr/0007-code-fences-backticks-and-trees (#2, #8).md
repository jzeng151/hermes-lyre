# 0007. Keep code fences and backticks, leave tree lines unchanged

Status: Accepted
Issue: #2, #8

## Context

Three formatter spec questions waited on the screen-reader baseline in #2:

- **Q1:** keep code fences on every client, or strip them on plain clients and keep them where the client renders code?
- **Q5:** do screen readers speak the backticks around inline code or the backslash in escapes? The backticks are the boundary that stops a second pass from changing code.
- **Q6:** do screen readers speak the box-drawing characters in an unfenced folder tree, which Lyre leaves unchanged?

The baseline sent one stored reply through Telegram with Lyre off and listened with NVDA on Windows and TalkBack on Android, both at default settings ([docs/baseline](../baseline/README.md)).

## Decision

- **Q1: keep fences on every profile.** Telegram shows fenced code as a block and neither screen reader speaks the fences. Core's opt-in WhatsApp plain-output formatter already requires fences there. Neither screen reader says where a code block starts or ends, so Lyre's `Python code, N lines:` and `End of code.` labels stay as the only spoken boundary.
- **Q5: keep the backticks.** Neither screen reader speaks them on Telegram, which shows the span as code. Prose backslash escapes stay as written for now: NVDA skips backslashes, TalkBack reads them, and Lyre does not make this worse than without it. Removing them where the bare character cannot become markup on a second pass is #51.
- **Q6: leave tree lines unchanged.** Both screen readers skip the box-drawing characters and read the names.

## Consequences

- No fence-stripping code: R7 stays as built in #8.
- With Lyre on, Telegram listeners hear the language twice: Lyre's label, then Telegram's own (#43).
- Inline code has no spoken boundary on either screen reader, and NVDA announces it as "edit" with a pause on each side. Lyre adds no label, to keep replies that mention many files or commands short; revisit if testers ask (#21).
- TalkBack users hear "backslash" for prose escapes until #51.
- Not tested: VoiceOver, WhatsApp and plain-text clients (Signal, SMS, iMessage). A plain-text client that shows fences literally would need a new record that supersedes this one.
- Speech-engine pronunciation (`us-east-1` read as "us", `auth` as "o", 4-digit numbers spoken fast) is out of the formatter's scope: Lyre never changes words or numbers. The README lists it as a limit.
