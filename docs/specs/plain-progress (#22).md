# Plain Progress Spec

Issue: #22 (stretch)
Design: [DESIGN.md](../../DESIGN.md)
Owner: @jzeng151
Status: Draft

## Goal

In a Telegram DM, a screen-reader user hears one short, plain line per finished step while Hermes works, kept in a single message that is edited in place, instead of silence or a stream of tool names and arguments.

## Non-goals

- No progress on the classic CLI, TUI, SMS or email. The CLI prints posted messages at the end of the turn, the TUI shows them in the repainting status line, and SMS and email send a new message per edit.
- No raw tool arguments, file paths, commands or results in any line.
- No model calls to describe a step.
- No progress for subagents or cron runs.
- No other messaging platforms until Telegram is tested with a screen reader.

## Contract

### Hooks

```python
ctx.register_hook("post_tool_call", on_tool_done)
```

`provides_hooks` becomes `[transform_llm_output, post_tool_call]`. `pre_tool_call` is not used: it fails closed, and `post_message` can block for up to 30 seconds.

### Message

- The first finished step in a turn calls `ctx.post_message(line)` and keeps the handle for that turn.
- Later steps call `handle.edit(text)` with all lines so far, one per line, numbered: `Step 1, searched the web.` `Step 2, command failed.`
- After 10 steps, earlier lines collapse into `Steps 1 to 7 finished.` so the message stays short.
- If `post_message` returns `ok=False`, progress is skipped for the rest of the turn.
- Handles are keyed by `turn_id` and dropped when the turn's final reply passes through the rewrite hook.

### Outcome lines

| Tool outcome | Line |
| --- | --- |
| `terminal` exit code 0 | `command finished.` |
| `terminal` non-zero exit | `command failed.` |
| file write or patch succeeded | `edited a file.` |
| file read | `read a file.` |
| web search | `searched the web.` |
| web extract or browser navigation | `read a web page.` |
| delegate task finished | `a helper task finished.` |
| any tool error | `a step failed.` |
| any other tool | not shown |

### Settings

| Key | Type | Default |
| --- | --- | --- |
| `progress` | bool | false |

Progress runs only when `enabled`, `messaging` and `progress` are all true and the platform is `telegram` in a direct message.

## Acceptance Criteria

- [ ] **AC-1** Given a Telegram DM with progress on, when Hermes runs three tools, then one message shows three numbered lines and the final reply arrives after it.
- [ ] **AC-2** Given any line, then it contains no tool arguments, paths, commands or output.
- [ ] **AC-3** Given the CLI, TUI, a Telegram group, SMS or email, when tools run, then no progress message is posted.
- [ ] **AC-4** Given `post_message` fails, when later tools finish, then no further attempt is made in that turn and the final reply is unaffected.
- [ ] **AC-5** Given built-in tool progress is also on, when tools run, then the README-recommended configuration shows no duplicate progress.
- [ ] **AC-6** Given a screen reader on Telegram, when the message is edited, then the edit is announced or discoverable without re-reading the whole chat.

## Edge Cases

- **No tools in a turn:** no progress message.
- **Duplicates:** the same tool finishing twice gives two lines.
- **Concurrency:** parallel tool calls in one turn append in completion order; edits are serialized per turn.
- **Interrupted turn:** the handle is dropped; the last edited message stays as is.
- **Permissions:** only the current conversation; `post_message` cannot reach other chats.

## Open Questions

- [ ] **Q1** Does Telegram announce message edits to TalkBack or VoiceOver, or does the user have to find the message again? Decides whether edit-in-place is usable at all.
- [ ] **Q2** Should Lyre recommend turning built-in tool progress off on Telegram, or detect it? Built-in progress settings are core config, not Lyre's.
- [ ] **Q3** What tool names does the `post_tool_call` payload use for file, web and browser tools at v0.23.0? The outcome table must match them exactly.

## Output / Deliverables

- Code: `lyre/progress.py`, registration in `lyre/__init__.py`, `progress` key in `config_schema`.
- Tests: `lyre/tests/test_progress.py` with a fake `post_message` handle.
- Rollback: `progress: false`.
