# 0008. Keep emoji without a spoken word

Status: Accepted
Issue: #5

## Context

R4 turned the status emoji (done, failed, warning, red, yellow, green, pending) into words and removed every other emoji under the default `words` policy. Many of those emoji carry meaning, not decoration. Removing them changed what a reply said:

- `The answer is 🇫🇷, not 🇩🇪.` became `The answer is, not.`
- `Use key 1️⃣ to continue.` became `Use key to continue.`
- `Rated ⭐⭐⭐⭐ out of 5` became `Rated out of 5`.
- `Temp 30°C ☀️ today` became `Temp 30°C today`.

Lyre stores its rewrite in the session, so the model and later turns lose the information too. Screen readers such as NVDA and TalkBack already speak a name for the emoji they know, so leaving an emoji in place lets the listener hear it.

## Decision

Under `emoji_policy: words`, only the status emoji in the R4 table become words. Every other emoji is kept as written, byte for byte, with its whole sequence (variation selectors, skin tones, joiner sequences, keycaps, flags).

- A run mixing status and other emoji keeps its order: `✅ 🎉 ⚠️` -> `(done) 🎉 (warning)`. Each status word is set off by one space; kept emoji keep the gaps they had between them.
- A run with no status emoji is left exactly as written, spacing included. The emoji rule then changes nothing on a second pass.
- Decorative emoji are kept too, such as `🚀` at the start of a heading or `✨` around a sentence. Telling decoration from meaning would need guesses Lyre cannot make reliably.
- `emoji_policy: remove` still removes every emoji, status emoji included, and is documented as losing information. `emoji_policy: keep` still skips the rule.

This replaces the `any other emoji | removed` row of R4. ADR 0004, which decides what counts as an emoji, is unchanged.

## Consequences

- No information is lost under the default policy: flags, keycaps, ratings, weather and reaction emoji reach the listener.
- Cost: speech is noisier. Decorative emoji are spoken by name, TalkBack adds the word "emoji" after the name, and NVDA says "Unlabeled graphic" for some emoji its symbol table does not know. Users who prefer silence can choose `emoji_policy: remove`.
- A line made of an emoji and box-drawing characters (`🎉 ───`) is no longer removed under `words`, because it is no longer drawing-only once the emoji stays.
- Tests that asserted removal of other emoji under `words` now assert it under `remove`, so the spacing and delimiter fixes for removed emoji keep their coverage.
