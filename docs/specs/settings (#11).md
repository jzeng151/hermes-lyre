# Settings Spec

Issue: #11
Design: [DESIGN.md](../../DESIGN.md)
Owner: @jzeng151
Status: Review

## Goal

Every Lyre behavior a user may want to change is a validated setting with a safe default, editable from `/a11y`, the Desktop Plugins form, or `hermes config set`, and read live by the hook.

## Non-goals

- No per-chat, per-user or per-session settings.
- No secrets, environment variables or plugin state files.
- No settings for the stretch features until those features ship. Each stretch spec adds its own keys.

## Contract

Declared in `lyre/plugin.yaml` under `config_schema`. Stored at `plugins.entries.lyre.settings.<key>`. Flat keys only, so the Desktop form renders switches and dropdowns instead of a JSON editor.

```yaml
config_schema:
  enabled:      {type: bool, default: false, label: "Lyre is on", description: "Master switch. /a11y on and /a11y off change this."}
  messaging:    {type: bool, default: true,  label: "Messaging apps", description: "Telegram, WhatsApp, Signal, Discord, Slack and other chats."}
  email:        {type: bool, default: true,  label: "Email"}
  cli:          {type: bool, default: true,  label: "Classic terminal"}
  tui:          {type: bool, default: true,  label: "Terminal UI"}
  cron:         {type: bool, default: true,  label: "Scheduled tasks", description: "Results of cron jobs delivered to you."}
  desktop:      {type: bool, default: false, label: "Desktop app", description: "Desktop already renders headings and tables."}
  api:          {type: bool, default: false, label: "API, editors and agent-to-agent", description: "Programs may parse markdown; leave off unless you read these replies yourself."}
  verbosity:    {type: str, choices: [brief, normal, full], default: normal, label: "Verbosity"}
  emoji_policy: {type: str, choices: [words, remove, keep], default: words, label: "Emoji", description: "words: status emoji become words, others are removed."}
  table_style:  {type: str, choices: [sentences, unchanged], default: sentences, label: "Tables"}
```

### Read API (internal)

```python
@dataclass(frozen=True)
class LyreSettings:
    enabled: bool
    groups: Mapping[str, bool]   # messaging, email, cli, tui, cron, desktop, api
    verbosity: str
    emoji_policy: str
    table_style: str

def load_settings(ctx) -> LyreSettings
```

- Reads each key with `ctx.get_config(key, default=...)`.
- Never raises. Invalid values fall back to the default.
- Not cached in module globals; called once per hook call and per command.

### Write API (internal)

```python
def set_setting(ctx, key: str, value) -> None
```

- Validates `key` against the schema and `value` against its type and choices before calling `ctx.set_config`.
- Raises `ValueError` with a plain-sentence message on invalid input; the command turns it into a reply.

### Validation

| Problem | Behavior | Log |
| --- | --- | --- |
| Missing key | Default | none |
| Wrong type (`"yes"` for a bool) | Default for that key | One `WARNING` per process per key: `lyre: setting <key> has invalid value; using default <default>` |
| Value not in `choices` | Default for that key | Same warning |
| Unknown extra keys | Ignored | none |

Bool strings are not coerced. Hermes validates types at load and the Desktop form only writes valid values; anything else is a hand edit and falls back to the default.

## Acceptance Criteria

- [ ] **AC-1** Given a fresh install, when settings are loaded, then every key has its default and `enabled` is false.
- [ ] **AC-2** Given `verbosity: loud` in config, when settings are loaded, then verbosity is `normal` and one warning is logged.
- [ ] **AC-3** Given the Desktop Plugins page, when Lyre's settings open, then every key shows as a switch or dropdown with its label and description.
- [ ] **AC-4** Given the user switches "Desktop app" on in the form and saves, when the next Desktop reply arrives with Lyre on, then it is rewritten.
- [ ] **AC-5** Given `hermes config set plugins.entries.lyre.settings.verbosity brief`, when the next reply arrives, then brief output is used.
- [ ] **AC-6** Given `set_setting(ctx, "verbosity", "loud")`, then it raises `ValueError` and config is unchanged.
- [ ] **AC-7** Given `hermes plugins validate`, then the `config_schema` check passes.

## Edge Cases

- **Empty values:** an empty string for a choice key falls back to the default.
- **Duplicates:** repeated writes of the same value are harmless; `ctx.set_config` is atomic.
- **Concurrency:** a Desktop save and a `/a11y` command at the same moment: last write wins per key; both writes are atomic.
- **Permissions:** Lyre writes only under its own namespace; `ctx.set_config` rejects anything else.
- **Profiles:** each Hermes profile has its own settings. Documented in the README.

## Test Checklist

- [ ] Defaults with an empty config (AC-1).
- [ ] Each invalid-value class (AC-2, AC-6).
- [ ] Round trip: `set_setting` then `load_settings` (AC-5 logic).
- [ ] Desktop form check, manual (AC-3, AC-4).
- [ ] `hermes plugins validate` in CI (AC-7).

## Output / Deliverables

- Code: `lyre/settings.py`, `config_schema` in `lyre/plugin.yaml`.
- Tests: `lyre/tests/test_settings.py`.
- Rollback: removing a key later must keep reading old configs without error (unknown keys are ignored).
