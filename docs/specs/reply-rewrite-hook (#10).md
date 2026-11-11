# Reply Rewrite Hook Spec

Issue: #10
Design: [DESIGN.md](../../DESIGN.md)
Owner: @jzeng151
Status: Review

## Goal

Every final reply on a surface where Lyre is on is replaced by `format_for_speech` output before Hermes delivers and stores it, and Lyre can never cost the user a reply.

## Non-goals

- No `hold_stream`. Streamed text on surfaces with streaming on is not intercepted.
- No rewriting of commentary between tool calls, tool progress, reasoning, or Hermes's own trailers (file-mutation warning, abnormal-exit note). Hermes appends trailers after the hook.
- No per-chat or per-user settings. Settings are profile-wide.

## Contract

### Registration

```python
ctx.register_hook("transform_llm_output", on_final_reply)
```

Registered once in `register(ctx)`, unconditionally, with no `hold_stream`. `provides_hooks: [transform_llm_output]` in `lyre/plugin.yaml` (already in the scaffold).

### Input

| Field | Type | Use |
| --- | --- | --- |
| `response_text` | `str` | The text to rewrite. |
| `platform` | `str` | Surface resolution (below). |
| `session_id` | `str` | Ignored except in debug logs. May be empty. |
| `model` | `str` | Ignored. |
| `turn_id` | `str` | Log correlation only. |
| `**kwargs` | | Accepted and ignored, so new fields do not break the hook. |

### Output

- `str`: the rewrite. Returned only when it differs from `response_text`.
- `None`: leave the reply unchanged. Returned when Lyre is off, the surface is off, the formatter made no change, or anything failed.
- Never an empty string.

### Surface resolution

| `platform` | Group | Setting read | Profile |
| --- | --- | --- | --- |
| `telegram`, `discord`, `slack`, `matrix`, `teams`, `mattermost`, `google_chat` | messaging | `messaging` | markdown |
| `whatsapp`, `whatsapp_cloud`, `signal`, `sms`, `bluebubbles`, `photon`, `irc`, `line`, `simplex`, `feishu`, `dingtalk`, `wecom`, `weixin`, `qqbot`, `yuanbao`, `buzz`, `raft`, `ntfy` | messaging | `messaging` | plain |
| `email` | email | `email` | plain |
| `cli` | cli | `cli` | plain |
| `tui` | tui | `tui` | plain |
| `cron` | cron | `cron` | plain |
| `desktop` | desktop | `desktop` | markdown |
| `api_server`, `acp`, `a2a`, `webhook` | api | `api` | markdown |
| `subagent` | none | never on | n/a |
| empty string | none | never on | n/a |
| any other value | messaging | `messaging` | plain |

Platform matching is case-insensitive. Unknown values are treated as messaging because new chat platforms arrive as plugins, and the plain profile is the safe default.

### Decision order

1. `platform` is `subagent` or empty: return `None`.
2. `enabled` setting is false: return `None`.
3. The group's setting is false: return `None`.
4. Call `format_for_speech(response_text, profile=..., verbosity=..., emoji_policy=..., table_style=...)` with settings from [settings.md](settings%20%28%2311%29.md).
5. Result equals `response_text`, or is empty or whitespace-only: return `None`. Otherwise return the result. (The formatter already returns its input instead of an empty result; this check keeps the hook's "never an empty string" contract even if it does not.)

Settings are read on every call through `ctx.get_config`, so changes made by `/a11y` or the Desktop form apply to the next reply.

### Errors

| Condition | Behavior | Log |
| --- | --- | --- |
| Any exception in steps 1 to 5 | Return `None` | One `WARNING`: `lyre: rewrite skipped (<ExceptionType>) turn=<turn_id>`. No reply text, no traceback with locals. |
| Formatter took longer than 200 ms | Return the result | One `INFO` with the duration and input length, no reply text. |
| Invalid setting value | Use the default for that key | Handled in [settings.md](settings%20%28%2311%29.md). |
| Hook exceeds `plugins.hook_callback_timeout` | Hermes abandons the call and delivers the original | Hermes logs it; nothing for Lyre to do. |

### Behavior by surface

| Surface | What the user gets |
| --- | --- |
| Messaging (streaming off, the default) | Only the rewrite. |
| Messaging with streaming turned on | The raw reply streams, then the final message is the rewrite. Documented as a limit. |
| Classic CLI, `display.streaming` off (the default) | Only the rewrite. |
| Classic CLI, `display.streaming` on | Raw reply streams, then the rewrite prints. README tells CLI users to turn streaming off. |
| TUI | The final message is replaced by the rewrite. |
| Cron | The delivered result is the rewrite. |
| Desktop, API, ACP | Unchanged unless the user turned that group on. |

## Acceptance Criteria

- [ ] **AC-1** Given Lyre is off, when any reply arrives on any platform, then the hook returns `None`.
- [ ] **AC-2** Given Lyre is on, when a reply arrives with `platform="subagent"` or `platform=""`, then the hook returns `None`.
- [ ] **AC-3** Given Lyre is on with defaults, when the same markdown reply arrives on `telegram`, `whatsapp`, `email`, `cli`, `tui` and `cron`, then each returns a rewrite with the profile from the table; and on `desktop`, `api_server` and `acp` it returns `None`.
- [ ] **AC-4** Given Lyre is on, when a reply has nothing to change, then the hook returns `None`.
- [ ] **AC-5** Given the formatter raises, when the hook runs, then it returns `None` and logs one warning with no reply text.
- [ ] **AC-6** Given `/a11y off` was run, when the next reply arrives, then the hook returns `None` with no reload or restart.
- [ ] **AC-7** Given an unknown platform `newchat`, when Lyre is on, then the reply is rewritten with the plain profile.
- [ ] **AC-8** Given a 20 KB reply, when the hook runs, then it returns in under 50 ms excluding the settings read.
- [ ] **AC-9** Given a 9-row table reply on Telegram, when the session is resumed and the user asks for the value in row 9, then the model answers correctly from the stored rewrite. (Live test, [release-evidence.md](release-evidence%20%28%2316%2C%20%2317%2C%20%2319%29.md).)
- [ ] **AC-10** Given a 5-turn conversation with Lyre on, when replies are compared with Lyre off, then no turn loses a table cell, URL or code line.
- [ ] **AC-11** Given Lyre is on and a reply that is only `🎉`, or a formatter stub that returns `""` or whitespace, then the hook returns `None` and the original reply is delivered.

## Edge Cases

- **Empty reply:** Hermes does not fire the hook for empty or interrupted turns. If it does, the formatter returns it unchanged and the hook returns `None`.
- **Error and budget-summary replies:** rewritten like any reply.
- **Duplicates:** the hook fires once per turn; Hermes records the outcome per `turn_id`. Lyre keeps no per-turn state.
- **Concurrency:** multiple sessions call the hook in parallel. The hook keeps no shared mutable state; settings are read, never cached in module globals.
- **Another rewrite plugin:** first non-empty rewrite wins. If another plugin rewrites first, Lyre's callback may not run or its result is ignored. Documented in the README; the plugin API cannot detect it (Q1 in [a11y-command.md](a11y-command%20%28%2312%29.md)).
- **Permissions:** none. Lyre reads only its own settings namespace.

## Test Checklist

- [ ] Happy path per surface group with a fake `ctx` (AC-3, AC-7).
- [ ] Off paths (AC-1, AC-2, AC-4, AC-6, AC-11).
- [ ] Error path with a formatter forced to raise; log captured and checked for absence of reply text (AC-5).
- [ ] Timing (AC-8).
- [ ] Live runs for AC-9 and AC-10 in [release-evidence.md](release-evidence%20%28%2316%2C%20%2317%2C%20%2319%29.md).

## Output / Deliverables

- Code: `lyre/hook.py`, registration in `lyre/__init__.py`.
- Tests: `lyre/tests/test_hook.py`, `lyre/tests/test_plugin_contract.py` (registered hooks equal `provides_hooks`).
- Rollback: `/a11y off` or disabling the plugin; past turns keep their stored rewrite.
