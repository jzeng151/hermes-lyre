# Screen-reader baseline (#2)

What screen readers say for a typical Hermes reply with Lyre off. The results settle formatter spec questions Q1, Q5 and Q6; the decisions are in [ADR 0007](../adr/0007-code-fences-backticks-and-trees%20%28%232%2C%20%238%29.md).

| File | What it is |
| --- | --- |
| [test-reply.md](test-reply.md) | The stored test reply (synthetic data): heading, status emoji, bold and italic, inline code, a 9-row table, a code block with `**`, `\|` and emoji inside, a nested list, a folder tree, a long signed URL |
| [probe-escapes.md](probe-escapes.md) | A short follow-up message with backslash escapes in prose and in inline code |
| [transcript-template.md](transcript-template.md) | What to record for each run |
| [telegram-nvda.md](telegram-nvda.md) | Telegram Desktop with NVDA on Windows: Speech Viewer transcript and findings |
| [telegram-talkback.md](telegram-talkback.md) | Telegram for Android with TalkBack: findings by ear |

Both runs used default screen-reader settings and were sent with `hermes send`, which goes through the Telegram adapter's normal formatting and never runs Lyre.

## Findings that apply to both screen readers

- Code fences are not spoken, and nothing says that a code block starts or ends. Only Telegram's own language label is read.
- Inline code is not announced as code, and its backticks are not spoken.
- Box-drawing characters in an unfenced folder tree and `-` list markers are skipped.
- Status emoji are noisy: "Unlabeled graphic" (NVDA) or "white heavy check mark emoji" (TalkBack).

## Where they differ

- Backslashes: NVDA skips them; TalkBack reads every one, in code and in prose. Telegram shows prose escapes with their backslash.
- NVDA pauses before and after every bold, italic or inline-code run and announces inline code as "edit". TalkBack does neither.

## Demo client

Telegram. Its baseline is clearly bad (emoji read as graphics or long names, broken-up sentences on NVDA), which is what the before/after recording in #17 needs to show.

## Not tested

VoiceOver, WhatsApp, and plain-text clients (Signal, SMS, iMessage).
