# Design Doc: Lyre

Spec: [docs/specs/](docs/specs/README.md)
Owner: @jzeng151
Status: Review

Lyre is an opt-in Hermes plugin that makes Hermes's final replies easy to follow by ear for people who use VoiceOver, NVDA, JAWS or TalkBack. It does not add a voice. It cleans the text Hermes sends to the screen reader the user already has.

## Context

### Problem

Hermes replies are written for sighted readers of rendered markdown. On messaging apps and in the terminal, a screen reader reads that markup aloud: "star star", emoji names such as "red circle", and every pipe and dash of a table. Code gives no warning of where it starts or ends. Lists lose their nesting. The worst cases are plain-text clients (WhatsApp, SMS, Signal, iMessage), where nothing is rendered at all.

A skill or system prompt can only ask the model to write plainly. It cannot cover text the model did not write (errors, budget summaries), and the model does not always comply. Lyre rewrites the final reply itself, after the model has finished.

### Users

- Primary: blind and low-vision Hermes users reading replies in a messaging app or terminal with a screen reader.
- Secondary: anyone who listens to Hermes replies, for example while driving with a phone reading messages aloud.

### Scope

| Tier | Item | Issue | Spec |
| --- | --- | --- | --- |
| Must | Speech formatter (pure function) | #3 to #9 | [speech-formatter](docs/specs/speech-formatter/spec%20%28%233-%239%29.md) |
| Must | Reply rewrite hook | #10 | [reply-rewrite-hook](docs/specs/reply-rewrite-hook%20%28%2310%29.md) |
| Must | Settings and Desktop form | #11 | [settings](docs/specs/settings%20%28%2311%29.md) |
| Must | `/a11y` command | #12 | [a11y-command](docs/specs/a11y-command%20%28%2312%29.md) |
| Must | Verification and release evidence | #13 to #17, #19 | [speech-formatter evidence](docs/specs/speech-formatter/test-evidence%20%28%233-%239%2C%20%2313-%2315%29.md), [release-evidence](docs/specs/release-evidence%20%28%2316%2C%20%2317%2C%20%2319%29.md) |
| Stretch | Plain progress in Telegram DMs | #22 | [plain-progress](docs/specs/plain-progress%20%28%2322%29.md) |
| Stretch | Accessible web chat tab | #23 | [accessible-web-chat](docs/specs/accessible-web-chat%20%28%2323%29.md) |
| Stretch | Bundled `write-for-ears` skill | #24 | none (content only) |
| Future | Readable approvals, prompt hint, terminal status line, Desktop focus | #25 to #28 | none (blocked) |

Must-tier work alone is a complete plugin. Stretch work starts only after the must tier passes its tests.

### Non-goals

- No text-to-speech. Lyre produces text for the user's own screen reader.
- No summarizing or shortening. Anything that needs a model call is out.
- No changes to Hermes core, no runtime overrides of core, no private core imports.
- No Desktop renderer code.
- No translation of inserted words. They are English only.
- No terminal status-line or Desktop focus fixes. Both need core changes (#27, #28).

## Architecture Decision

### Chosen approach

One public hook and one pure function:

```
model final reply
      |
      v
transform_llm_output(response_text, platform, ...)      <- Lyre hook (always registered)
      |   off for this surface, or unchanged  -> return None (Hermes keeps the original)
      |   on                                   -> format_for_speech(text, profile, settings)
      v
rewritten text: delivered to the user AND stored in the session
      |
      v
platform adapter's own format_message() (Telegram MarkdownV2, Discord, WhatsApp, ...)
      |
      v
client -> screen reader
```

- The hook is registered without `hold_stream`. Gateway streaming is off by default (`streaming.enabled: false`), so on messaging the rewrite is the only text the user receives.
- The hook is always registered and decides per call, reading settings live. `/a11y on` and `off` therefore apply to the next reply with no restart or reload.
- The formatter is a pure function with no I/O and no Hermes imports, so it is fully unit-testable and could move into core unchanged.

### Why this approach

- `transform_llm_output` runs once per turn on the final reply on every surface, and its return value is what is delivered and stored. Every way a turn ends passes through it, including errors and budget summaries.
- A non-held hook fails open. If Lyre raises or runs past the hook timeout (`plugins.hook_callback_timeout`, default 30 s), Hermes logs it and sends the original reply. The user never loses an answer because of Lyre.
- A pure formatter keeps reliability claims checkable: golden files, property tests and fuzzing need no Hermes runtime.

### Alternatives rejected

| Alternative | Why rejected |
| --- | --- |
| `hold_stream=True` on the hook | The hold covers every surface in the profile whenever the plugin is loaded, including Desktop, API and ACP. Turning it on needs a reload. A failing hook replaces the reply with a "reply withheld" notice, and commentary between tool calls is dropped. Streaming is already off on messaging by default, so the hold buys little. |
| System-prompt section asking for plain style | `register_system_prompt_section` is frozen into each session's prompt, so it cannot follow `/a11y` toggles without breaking the prompt cache. Deferred (#26). |
| Approval transport for readable approvals | A transport replaces the built-in prompt and needs its own channel to read the user's answer. Plugins have none, and a failure denies every approval. Cut (#25). |
| Shortening URLs, collapsing code, summarizing long replies | The rewrite is stored and replayed to the model, so anything removed is lost to later turns. Summaries need a model call. Rejected. |
| Per-platform patches inside adapters | Needs core changes. Catalog rule 9 forbids runtime overrides. |

## Interfaces

### Hermes APIs used

| API | Use | Notes |
| --- | --- | --- |
| `ctx.register_hook("transform_llm_output", cb)` | Rewrite the final reply | Payload: `response_text`, `session_id`, `model`, `platform`, `turn_id`. First non-empty string wins across plugins. |
| `ctx.register_command("a11y", handler, ...)` | `/a11y` | Handler may declare `platform`, `session_id`, `session_key`, `source`. Works in CLI, TUI, Desktop and every gateway chat. |
| `config_schema` in `lyre/plugin.yaml` | Settings and Desktop form | Values live under `plugins.entries.lyre.settings`. |
| `ctx.get_config` / `ctx.set_config` | Read settings live, write `/a11y` changes | `get_config` reads the cached config on every call; `set_config` writes atomically. |
| `ctx.session_surface()` | Resolve the surface when a command reports `platform="local"` | Returns `cli`, `tui`, `desktop`, `acp` or the messaging platform. |
| `ctx.post_message` | Stretch only (#22) | Edits in place on messaging; differs by surface. |

`plugin.yaml` declares `requires_hermes: ">=0.23.0"` and `provides_hooks: [transform_llm_output]`. The validator compares tools, hooks and middleware only; slash commands are not a capability field.

### Hook platform values

The `platform` value decides whether Lyre runs and how. Full mapping: [reply-rewrite-hook](docs/specs/reply-rewrite-hook%20%28%2310%29.md).

| `platform` | Surface group | Default when Lyre is on |
| --- | --- | --- |
| Messaging platforms (`telegram`, `whatsapp`, `signal`, `sms`, ...) | messaging | On |
| `email` | email | On |
| `cli` | cli | On |
| `tui` | tui | On |
| `cron` | cron | On |
| `desktop` | desktop | Off |
| `api_server`, `acp`, `a2a`, `webhook` | api | Off |
| `subagent` | none | Always off; not configurable |
| empty | none | Always off |

Subagent replies are returned to the parent model, not shown to a person, so rewriting them would only degrade the parent's input.

### Render profiles

Each surface gets one of two profiles:

- `plain`: the client shows text as-is. All presentation markup is converted to words or removed.
- `markdown`: the client renders bold, italics and headings, so those markers are left for the adapter. Emoji, tables, lists, code announcements, links and rules are still converted.

| Profile | Platforms |
| --- | --- |
| markdown | telegram, discord, slack, matrix, teams, mattermost, google_chat |
| plain | everything else, including whatsapp, sms, signal, bluebubbles, email, cli, tui, cron |

Unknown platforms get `plain`. Stripping a marker a client would have rendered loses only visual emphasis; leaving one a client shows raw is spoken aloud.

### Formatter

```python
def format_for_speech(
    text: str,
    *,
    profile: Literal["plain", "markdown"],
    verbosity: Literal["brief", "normal", "full"] = "normal",
    emoji_policy: Literal["words", "remove", "keep"] = "words",
    table_style: Literal["sentences", "unchanged"] = "sentences",
) -> str
```

Rules and exact output: [speech-formatter spec](docs/specs/speech-formatter/spec%20%28%233-%239%29.md).

### Storage

- Settings: `plugins.entries.lyre.settings` in the profile's `config.yaml`, through `ctx.set_config` only.
- No plugin state, no files, no database.

### Layout

The plugin lives in `lyre/` and is self-contained, matching the official Hermes plugin repositories: its README, LICENSE, `pytest.ini` and tests sit inside it, and the catalog entry points at it with `subdir: lyre`. The repository root holds the development README, LICENSE and CI only. The plugin has no dependencies, so Hermes installs nothing for it.

```
lyre/
  plugin.yaml          manifest: requires_hermes, provides_hooks, config_schema
  __init__.py          register(ctx): hook + command
  hook.py              transform_llm_output callback, surface resolution
  settings.py          typed read of settings with defaults and validation
  command.py           /a11y handler
  README.md            user README; rendered on the catalog page at the pinned commit
  LICENSE, pytest.ini
  formatter/           replaces the scaffold's lyre/formatter.py stub (task T1)
    __init__.py        format_for_speech
    core.py            line parser, protected spans, pipeline
    rules/             emphasis, headings, quotes, decoration, emoji, lists, tables, code, links
  tests/
    conftest.py, test_formatter.py   (from the scaffold)
    formatter/         unit, property, fuzz, performance
    golden/            corpus inputs, expected outputs, update_golden.py
    test_hook.py, test_settings.py, test_command.py, test_roundtrip.py
    test_plugin_contract.py   registered hooks equal provides_hooks (from the scaffold)
```

Tests run from the plugin folder: `cd lyre && uv run --no-project --with pytest --with pyyaml pytest`. CI runs them on Linux, macOS and Windows, and runs `hermes plugins validate` and `hermes plugins doctor lyre --ci` against Hermes v0.23.0 and main (main is non-blocking).

The scaffold's stub is `format_for_speech(text, *, platform, settings)`. This design replaces it with explicit keyword arguments (`profile`, `verbosity`, `emoji_policy`, `table_style`) so the formatter knows nothing about platforms or config; `hook.py` maps platform and settings to those arguments.

## Constraints

### Compatibility

- `requires_hermes: ">=0.23.0"`, tested on v0.23.0. Every API above exists at that release.
- Every adapter's own `format_message` runs after Lyre. Lyre's output must survive each one (#13).
- Core has an opt-in WhatsApp plain-output formatter. Lyre's status words match its labels (`(done)`, `(warning)`, `(red)`) and code must keep its fences where that formatter can run after Lyre, or it strips `**` and emoji from inside the code.
- Only one `transform_llm_output` rewrite wins per turn. Another rewrite plugin that registers first silently disables Lyre for that turn. Documented in the README.

### Information preservation

The rewrite is stored, and later turns, memory and session search see it. So:

- Every table cell, URL, code block and ambiguous symbol survives.
- URLs and code are byte-identical to the input.
- Tables too large or malformed to speak pass through unchanged.

### Security

- Standard library only. No network, no shell, no file reads, no credentials.
- No reply content in logs. Errors log the exception type and the turn id only.
- Disclosed behavior (catalog rule 13): Lyre rewrites every reply on enabled surfaces and the rewrite is stored, so the model, memory and session search see it. In the classic CLI with streaming on, the raw reply shows before the rewrite.

### Performance

- Line-by-line parsing with no backtracking regexes. Linear in input size.
- Under 50 ms for a 20 KB reply.
- Replies over 200 KB (UTF-8) are returned unchanged without parsing.

### Operational limits

- Settings are profile-wide, not per chat. Recommend a personal profile, not shared group chats.
- Inserted words are English only. Replies that are mostly non-Latin script get symbol cleanup only.
- Not available in safe-worker mode or the out-of-process plugin host if those skip transform hooks. Verified in #16 and stated in the README.

## Rollout Plan

### Phase 1: Formatter and hook

Formatter rules, hook, settings and `/a11y` built against unit, property and golden tests. Lyre is opt-in: installing it changes nothing until `/a11y on`.

### Phase 2: Live verification

Clean install on v0.23.0, `hermes plugins doctor --ci` and `validate`, the classic CLI, Telegram and a cron run, then a screen-reader before/after.

### Phase 3: Catalog

Pin a release commit, submit the catalog entry, run the community hackathon-judge preflight.

### Phase 4: Stretch

Plain progress, accessible web chat, `write-for-ears` skill, each behind its own setting.

### Stop signals

- The row-9 follow-up question fails after resuming a session (information lost in the stored rewrite).
- Any golden or property test shows changed code or URL bytes.
- An adapter round-trip test shows Lyre output re-spoken as symbols.
- The screen-reader before/after does not show a clear improvement on the chosen client.

### Rollback

- User: `/a11y off`, or disable the plugin. Takes effect on the next reply.
- Stored rewrites are not reverted. Earlier turns keep their spoken-style text. Disclosed in the README.
- Catalog: a new PR pins the previous SHA or removes the entry.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Stored rewrite changes how the model writes later turns | Model copies the spoken style; table structure lost from history | Never drop cells, URLs or code; 5-turn conversation test; disclose it |
| Hook raises or runs slow | Hermes logs it and sends the original reply | Catch everything, size cap, performance test |
| Information lost in the rewrite | Worse answers in later turns | Pass oversized and malformed tables through; row-9 acceptance test |
| Another rewrite plugin wins | Lyre skipped for that turn | Document in the README; the plugin API cannot detect other rewrite hooks |
| Core adds its own screen-reader formatting | Overlap on some platforms | Idempotent output, matching status words; README credits core work |
| Seen as belonging in core | Weaker reception | Position Lyre as the fastest way to users now and a tested design core can adopt |
| Name confusion | Review delay | Name is Lyre; no catalog collision |
