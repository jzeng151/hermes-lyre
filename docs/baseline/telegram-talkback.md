# Baseline notes: Telegram with TalkBack (#2)

- Client: Telegram for Android (version not recorded)
- Phone: Samsung Galaxy S26 Ultra, Android 17
- Screen reader: TalkBack (version not recorded), default settings
- Text-to-speech engine: not recorded. Galaxy phones ship both Samsung's and Google's engine and Samsung does not publish which is the default; it is shown under Settings > General management > Text-to-speech > Preferred engine.
- Lyre: off
- Sent with: `hermes send --to telegram --file docs/baseline/test-reply.md`, then the same for `docs/baseline/probe-escapes.md`
- Captured by ear (no speech log)

## Observations

- TalkBack reads exactly the text shown in the selected item.
- **Code block:** Telegram shows a block, but TalkBack does not announce it as code. It reads Telegram's `Python` label, then the contents, with nothing marking the end. Fences are not read out.
- **Inline code** (`npm test -- --grep refresh`, `retry\*limit`): read as ordinary text. Nothing says it is code, and the backticks are not read.
- **Backslashes:** every displayed backslash is read out. That includes the one inside inline code and the prose escapes in the probe: Telegram's adapter shows a prose escape such as `retry\*limit` with its backslash. NVDA skips them all.
- **Box-drawing characters** in the folder tree: skipped.
- **The `-` before list sub-items:** skipped.
- **Status emoji:** read by name with "emoji" appended (✅ is "white heavy check mark emoji").
- **Pauses** around bold, italic or inline code: none (unlike NVDA).
- **Speech-engine problems:**
  - `us-east-1` is read with "us" as a word, not "U S".
  - `auth` is read as "o".
  - 4-digit numbers (`1,204`, `2,310`, `4821`) are spoken noticeably faster than the rest.

The speech-engine problems are pronunciation, not markup. Lyre does not change the words or numbers of a reply (identifiers like `us-east-1` must survive exactly so the model and the listener can reuse them), so they are out of the formatter's scope and belong in the README's limits.

## Answers for the formatter spec

- **Q1 (code fences):** not spoken. Neither TalkBack nor NVDA says that a code block starts or ends; only Telegram's language label is read. Keeping fences costs nothing, and Lyre's "Python code, N lines:" and "End of code." labels are the only spoken boundary. With Lyre on, the language is heard twice.
- **Q5 (backticks and backslashes):** backticks are not spoken (Telegram displays the span as code). Every displayed backslash is spoken, in code and in prose. Inside code the backslash is part of the code and must stay; prose escapes are #51.
- **Q6 (box-drawing characters):** skipped. Unchanged tree lines are safe.
