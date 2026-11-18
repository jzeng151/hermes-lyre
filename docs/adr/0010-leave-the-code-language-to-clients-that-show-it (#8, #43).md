# 0010. Leave the code language to clients that show it

Status: Accepted
Issue: #8, #43

## Context

R7 puts a label before every code block, such as `Python code, 12 lines:`. The screen-reader baseline ([docs/baseline](../baseline/README.md)) found that Telegram shows its own language label above a fenced block, and both NVDA and TalkBack read it. With Lyre on, a Telegram listener hears the language twice: Lyre's label, then Telegram's `Python`.

The formatter knows only two render profiles, `plain` and `markdown`. Showing a language label is a separate property of the client: several `markdown` clients do not show one, and the profile also controls bold, headings and other markup that have nothing to do with code.

What Hermes sends to each client that renders fenced code:

- **Telegram:** the adapter converts the reply to MarkdownV2 and keeps the fence's language tag, which Telegram shows as a label on the block. Confirmed by the baseline with NVDA and TalkBack. This holds only for a fence the adapter recognizes, the same in the current adapter and the oldest supported Hermes release:
  - the opening line is exactly three backticks and an optional info string, after optional spaces or tabs (for example `` ```python `` or `` ```python title=x.py ``), and
  - the closing line is exactly three backticks, with only spaces or tabs around them, and
  - the fence is not inside a quote (the adapter does not treat `` > ``` `` as an opening fence).

  Any other fence reaches Telegram as escaped text with no label: tilde fences (`~~~python`), fences of four or more backticks (```` ````python ````), a three-backtick fence closed by four, and fences inside a quote.
- **Slack:** the adapter removes the language tag, because Slack would show it as literal text. Slack users hear the language only from Lyre.
- **Discord, Matrix, Mattermost:** the language tag is passed on (Matrix as a `language-` class on the code element). Whether the client shows it, and whether a screen reader reads it, has not been tested.
- **Teams, Google Chat, Desktop and the API:** not tested.
- **WhatsApp and the plain clients:** no language label is known to be shown.

## Decision

- Add a keyword argument to `format_for_speech`: `code_language: Literal["spoken", "client"] = "spoken"`, validated like the other options (ADR 0001). `spoken` keeps today's label. `client` means the client names the language itself, so the label leaves it out (`Code, 12 lines:`) for the fences listed above. Every other fence keeps the spoken language, because otherwise nobody would name it. Inside a quote the formatter always uses `spoken`.
- The hook passes `client` for `telegram` only. Every other platform, including unknown ones, gets `spoken`.
- A platform joins the `client` list only with evidence that its client shows the language and a screen reader reads it. Discord, Matrix, Mattermost, Teams, Google Chat and Desktop stay unverified until tested.

## Consequences

- Telegram listeners hear the language once, from Telegram, followed by Lyre's line count and `End of code.`.
- The formatter carries one piece of Telegram knowledge: which fences it shows as code. If another client is added with different rules, the option needs a new value rather than a wider meaning.
- `brief` verbosity is unchanged (`Code:`), as are blocks with no known language, non-Latin replies (no labels at all) and the `End of code.` line.
- Defaults are unchanged, so the golden corpus does not change.
- Both label forms match the existing label pattern, so a reply labelled under one setting is not relabelled under the other. A reply relayed from another surface into Telegram keeps its language in Lyre's label.
- If an unverified client turns out to show the language, adding it is a one-line change to the hook's list.
