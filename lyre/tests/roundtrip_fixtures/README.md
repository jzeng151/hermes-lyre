# Round-trip fixtures

One sample reply (`input.md`) as Lyre rewrites it for each platform (`<platform>.lyre.txt`), and as the platform's own Hermes formatter then sends it (`<platform>.final.txt`). `plain-text.final.txt` is Lyre's plain output after core's plain-text formatter, used for SMS and iMessage.

These are for review by eye. The tests in `tests/test_roundtrip.py` check the same properties on more replies. The outputs were made with Hermes v0.23.0; regenerate them when Hermes changes its formatters.

Notes from review:

- Telegram turns a kept heading into bold and escapes punctuation for MarkdownV2. The escapes are not displayed.
- Slack drops a code fence's language tag. Lyre's code label already names the language.
- Discord splits long spoken tables at its 2,000-character limit and adds a marker such as (1/2) to each part.
