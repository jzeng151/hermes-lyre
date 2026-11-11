# Lyre

Lyre rewrites Hermes replies so they read clearly with a screen reader, on messaging apps, email and the terminal.

## Install and turn on

Install the plugin:

    hermes plugins install jzeng151/hermes-lyre/lyre

Answer yes when Hermes asks to enable it. If you said no, run `hermes plugins enable lyre`.

Lyre changes nothing until you turn it on. In any chat with Hermes, send:

    /a11y on

Your next reply is written for a screen reader. To stop, send `/a11y off`.

## Before and after

Here is a reply as Hermes writes it. A screen reader would read the pound signs, stars, pipes and emoji names aloud.

    ## Build results ✅

    The **deploy** finished. Two checks need a look:

    | Check | Status | Time |
    |---|---|---|
    | Unit tests | ✅ passed | 42 s |
    | Lint | ⚠️ 3 warnings | 8 s |

    1. Fix the warnings in `app.py`
    2. Re-run with:

    ```bash
    make lint
    ```

    See [the CI run](https://ci.example.test/runs/1234) for details 🎉

Here is the same reply after Lyre, as you would hear it:

    Build results (done).

    The deploy finished. Two checks need a look:

    Table, 2 rows, 3 columns: Check, Status, Time.
    Row 1: Check Unit tests, Status (done) passed, Time 42 s.
    Row 2: Check Lint, Status (warning) 3 warnings, Time 8 s.
    End of table.

    2 items.
    1, Fix the warnings in `app.py`
    2, Re-run with:

    Bash code, 1 line:
    ```bash
    make lint
    ```
    End of code.

    See the CI run, link: https://ci.example.test/runs/1234 for details

## What changes

- Headings become sentences. Bold, italic and strikethrough markers are removed.
- Status emoji become words: done, warning, failed, pending, and the colours red, yellow and green. Other emoji are removed.
- Tables become sentences, one row at a time, with each value named by its column.
- Lists announce how many items they have, and nested items say they are sub-items.
- Code gets a line before it naming the language and length, and "End of code." after it. The code itself is never changed.
- Links keep their full address after the word "link", so nothing is lost.
- Replies mostly in a script other than Latin keep their emoji and gain no English words.

Code, web addresses and math are never changed. Box-drawing trees, Braille and anything Lyre cannot read with confidence are left as written.

## What changes on each platform

- Messaging apps such as Telegram, WhatsApp, Signal, Discord and Slack: on by default once Lyre is on.
- Email: on by default.
- The classic terminal and the terminal UI: on by default.
- Scheduled tasks: on by default, for results delivered to you.
- The Desktop app: off by default, because it already shows headings and tables.
- The API, editors and agent-to-agent sessions: off by default, because programs may read the Markdown.

On Telegram, Discord, Slack, Matrix, Teams, Mattermost and Google Chat, the app shows Markdown, so Lyre keeps formatting the app turns into real bold or code. On WhatsApp, SMS, Signal, email, the terminal and every other app, Lyre writes plain text.

## Commands

- `/a11y on` turns Lyre on, including for the app you send it from.
- `/a11y off` turns Lyre off. Replies are sent as written.
- `/a11y status` says whether Lyre is on, and whether it is on for this app.
- `/a11y verbosity brief`, `normal` or `full` sets how much Lyre announces. Brief is shortest: no item counts, table rows without column names, and code without its language. Full adds "List," and "End of list.", announces quotes, and repeats table column names every ten rows.

These settings apply to every chat on the same Hermes profile. In a group chat, Lyre says so.

## Settings

You can also change these in the Hermes settings for the plugin. Each is listed with its default.

- Lyre is on: off.
- Messaging apps: on.
- Email: on.
- Classic terminal: on.
- Terminal UI: on.
- Scheduled tasks: on.
- Desktop app: off.
- API, editors and agent-to-agent: off.
- Verbosity: normal. The choices are brief, normal and full.
- Emoji: words. The choices are words, remove and keep.
- Tables: sentences. The choices are sentences and unchanged.

## Limits

- In the classic terminal with streaming turned on, you hear the original reply as it streams, then the rewrite. Turn streaming off in the terminal for the best result.
- The terminal status line and keyboard focus in the Desktop app need changes in Hermes itself. Lyre cannot fix them.
- Lyre may not run in safe-worker mode or in the out-of-process plugin host, if those skip reply hooks.
- Another plugin that also rewrites replies can conflict with Lyre. Use one at a time.
- Very long replies, over 200,000 bytes, are sent as written.

## What Lyre does with your replies

Lyre rewrites every reply on the surfaces you turn on. Hermes stores the rewritten reply, so the model, memory and session search see the rewrite, not the original.

Lyre reads no files and makes no network calls. It uses only the Python standard library. If anything goes wrong while rewriting, the original reply is sent unchanged.

## Relationship to Hermes

Lyre builds on the work in Hermes core on plain output for WhatsApp, and uses the same status words. The formatter has no Hermes imports and could move into core as it is.

Lyre has been tested with its own unit, property and fuzz tests. Results with real screen readers on each app will be listed here as they are recorded.

## Report a problem

If a reply is hard to follow, open an issue at https://github.com/jzeng151/hermes-lyre/issues. Paste the reply as Hermes wrote it, if you can, and say which app and screen reader you use. Plain text is fine.
