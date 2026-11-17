# 0010. Leave the code language to clients that show it

Status: Accepted
Issue: #8, #43

## Context

R7 puts a label before every code block, such as `Python code, 12 lines:`. The screen-reader baseline ([docs/baseline](../baseline/README.md)) found that Telegram shows its own language label above a fenced block, and both NVDA and TalkBack read it. With Lyre on, a Telegram listener hears the language twice: Lyre's label, then Telegram's `Python`.

The formatter knows only two render profiles, `plain` and `markdown`. Showing a language label is a separate property of the client: several `markdown` clients do not show one, and the profile also controls bold, headings and other markup that have nothing to do with code.

What Hermes sends to each client that renders fenced code:

- **Telegram:** the adapter converts the reply to MarkdownV2 and keeps the fence's language tag, which Telegram shows as a label on the block. Confirmed by the baseline with NVDA and TalkBack.
- **Slack:** the adapter removes the language tag, because Slack would show it as literal text. Slack users hear the language only from Lyre.
- **Discord, Matrix, Mattermost:** the language tag is passed on (Matrix as a `language-` class on the code element). Whether the client shows it, and whether a screen reader reads it, has not been tested.
- **Teams, Google Chat, Desktop and the API:** not tested.
- **WhatsApp and the plain clients:** no language label is known to be shown.

## Decision

- Add a keyword argument to `format_for_speech`: `code_language: Literal["spoken", "client"] = "spoken"`, validated like the other options (ADR 0001). `spoken` keeps today's label. `client` means the client names the language itself, so the label leaves it out: `Code, 12 lines:`.
- The hook passes `client` for `telegram` only. Every other platform, including unknown ones, gets `spoken`.
- A platform joins the `client` list only with evidence that its client shows the language and a screen reader reads it. Discord, Matrix, Mattermost, Teams, Google Chat and Desktop stay unverified until tested.

## Consequences

- Telegram listeners hear the language once, from Telegram, followed by Lyre's line count and `End of code.`.
- `brief` verbosity is unchanged (`Code:`), as are blocks with no known language, non-Latin replies (no labels at all) and the `End of code.` line.
- Defaults are unchanged, so the golden corpus does not change.
- Both label forms match the existing label pattern, so a reply labelled under one setting is not relabelled under the other. A reply relayed from another surface into Telegram keeps its language in Lyre's label.
- If an unverified client turns out to show the language, adding it is a one-line change to the hook's list.
