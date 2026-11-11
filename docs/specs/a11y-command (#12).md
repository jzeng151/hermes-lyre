# /a11y Command Spec

Issue: #12
Design: [DESIGN.md](../../DESIGN.md)
Owner: @jzeng151
Status: Review

## Goal

A screen-reader user can turn Lyre on and off, check its state and change verbosity from any chat or terminal with one short command, and hears a plain-sentence reply every time.

## Non-goals

- No per-chat or per-user state. The command changes profile-wide settings.
- No editing of emoji policy, table style or individual surface groups other than the current one. Those live in the settings form and `hermes config set`.
- No confirmation prompts.

## Contract

```python
ctx.register_command(
    "a11y",
    handler=handle_a11y,
    description="Screen-reader friendly replies: on, off, status, verbosity",
    args_hint="on | off | status | verbosity brief|normal|full",
)

def handle_a11y(raw_args: str, *, platform: str = "", source=None, **kwargs) -> str
```

Command replies are not model output and do not pass through `transform_llm_output`, so every reply below is written plain: no markdown, no emoji, no tables.

### Surface of the caller

- `platform` from the handler keywords, lowercased.
- If it is `local` or empty, use `ctx.session_surface()`.
- Map to a surface group with the table in [reply-rewrite-hook.md](reply-rewrite-hook%20%28%2310%29.md). `{surface}` in replies is a readable name: "Telegram", "WhatsApp", "the terminal", "the terminal UI", "the Desktop app", "email", "scheduled tasks", "API and editor sessions".

### Subcommands

Arguments are case-insensitive and trimmed. Extra words after a valid subcommand are an error.

| Input | Writes | Reply |
| --- | --- | --- |
| `/a11y` or `/a11y status` | nothing | See Status replies |
| `/a11y on` | `enabled=true`; the caller's group `=true` | `Lyre is on. Replies in {surface} will be written for screen readers, starting with the next one.` |
| `/a11y off` | `enabled=false` | `Lyre is off. Replies will be sent as written.` |
| `/a11y verbosity brief` (or `normal`, `full`) | `verbosity` | `Verbosity is now brief.` |
| `/a11y verbosity` | nothing | `Verbosity is normal. Choose brief, normal or full.` |
| `/a11y help` | nothing | Usage reply |
| anything else | nothing | Usage reply |

Usage reply: `Usage: /a11y on, /a11y off, /a11y status, or /a11y verbosity followed by brief, normal or full.`

`/a11y on` turns on the caller's group as well as the master switch, so a Desktop user can opt in from Desktop without opening settings. It writes the group first (skipped when already on) and `enabled` last, so a failure never leaves Lyre on without the caller's surface: if the group write fails nothing has changed, and if the `enabled` write fails Lyre is still off, and a group switched on while Lyre is off changes no reply. `/a11y off` turns off the master switch only, leaving the group choices for next time.

### Status replies

- Off: `Lyre is off. Type /a11y on to turn it on.`
- On, caller's group on: `Lyre is on for {surface}. Verbosity is normal.`
- On, caller's group off: `Lyre is on, but off for {surface}. Type /a11y on here to include {surface}.`
- No warning about other rewrite plugins: the plugin API cannot see them (Q1). The README covers the conflict.

### Shared-chat notice

When `source` is present and `source.chat_type` is not a direct message, `/a11y on` and `/a11y off` append: `This setting applies to every chat on this Hermes profile.`

### Errors

| Condition | Reply | Log |
| --- | --- | --- |
| `ctx.set_config` raises on `/a11y off` or `verbosity` (one write) | `Lyre could not save that setting. Nothing changed.` | One `WARNING` with the exception type |
| `ctx.set_config` raises on `/a11y on` | `Lyre could not be turned on. Lyre is still off.` (or `Lyre is still on.` if it already was) | One `WARNING` with the exception type and which key failed |
| Invalid verbosity value | `Verbosity must be brief, normal or full.` | none |
| Surface unknown (`subagent`, empty after fallback) | Apply the write, reply without the surface: `Lyre is on.` | none |

## Acceptance Criteria

- [ ] **AC-1** Given Lyre is off, when the user sends `/a11y on` in Telegram, then `enabled` and `messaging` are true and the reply names Telegram.
- [ ] **AC-2** Given Lyre is on with `desktop` false, when the user sends `/a11y on` in Desktop, then `desktop` becomes true and the next Desktop reply is rewritten.
- [ ] **AC-3** Given Lyre is on, when the user sends `/a11y off`, then `enabled` is false, group settings are unchanged, and the next reply is not rewritten.
- [ ] **AC-4** Given any state, when the user sends `/a11y status`, then nothing is written and the reply matches one of the status forms.
- [ ] **AC-5** Given `/a11y verbosity full`, then `verbosity` is `full`; given `/a11y verbosity loud`, then nothing changes and the error reply is sent.
- [ ] **AC-6** Given `/a11y banana`, then nothing changes and the usage reply is sent.
- [ ] **AC-7** Given a group chat, when `/a11y on` is sent, then the shared-chat notice is appended.
- [ ] **AC-8** Given Hermes restarts, when the user sends `/a11y status`, then the state from before the restart is reported.
- [ ] **AC-9** Given every reply text in this spec, then none contains `*`, `_`, `#`, `|`, a backtick or an emoji.
- [ ] **AC-10** Given the classic CLI, the TUI and a gateway chat, when `/a11y status` is sent, then each gets a reply.
- [ ] **AC-11** Given `/a11y on` while Lyre is off and the second write (`enabled`) fails, then `enabled` is still false, the reply says Lyre is still off, and the next reply on every surface is unchanged.

## Edge Cases

- **Empty input:** treated as `status`.
- **Duplicates:** `/a11y on` twice gives the same reply and the same settings.
- **Concurrency:** two chats toggling at once: last write wins; each reply reflects its own write.
- **Permissions:** any user allowed to talk to the Hermes profile can run `/a11y`. Gateway authorization already limits who that is. Documented in the README for shared profiles.
- **Name conflict:** if a future core command named `a11y` exists, Hermes rejects the plugin registration with a warning. `/a11y status` cannot report this; `hermes plugins doctor` and the README cover it.

## Open Questions

- [x] **Q1** Is there a public plugin API to list other loaded `transform_llm_output` callbacks? **No.** `PluginContext` exposes no listing; the manager's `list_plugins()` gives hook counts, not names, and is not part of the plugin API (v0.23.0). The conflict is documented in the README only.
- [ ] **Q2** Does `ctx.session_surface()` return the right surface inside a command handler when `platform` is `local`? Verified in the live runs (#16).

## Test Checklist

- [ ] Each subcommand with a fake `ctx` recording `set_config` calls (AC-1 to AC-6), including write order for `/a11y on`.
- [ ] Fake `ctx` whose `set_config` fails on the first or second key (AC-11).
- [ ] Shared-chat notice with a fake `source` (AC-7).
- [ ] Reply text lint for spoken symbols (AC-9).
- [ ] Live: CLI, TUI, Telegram, restart persistence (AC-8, AC-10).

## Output / Deliverables

- Code: `lyre/command.py`, registration in `lyre/__init__.py`.
- Tests: `lyre/tests/test_command.py`.
- Rollback: the command only writes settings; `/a11y off` or the settings form restores behavior.
