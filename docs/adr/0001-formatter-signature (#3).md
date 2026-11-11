# 0001. The formatter takes explicit options

Status: Accepted
Issue: #3

## Context

The setup scaffold shipped a stub `format_for_speech(text, *, platform, settings)`. The design doc and formatter spec instead define `format_for_speech(text, *, profile, verbosity, emoji_policy, table_style)`. One had to win before any rule was written.

## Decision

Use the spec's explicit keyword arguments. The formatter knows nothing about Hermes platforms or the settings store; the hook maps the hook's `platform` value and the plugin settings to a render profile and option values.

Invalid option values raise `ValueError` naming the bad value and the allowed ones. That is a bug in the caller, not a property of the reply, so it is the one case where the formatter raises.

## Consequences

- Tests state exactly what they cover (`profile="plain", verbosity="brief"`) with no fake settings objects.
- The formatter can move into Hermes core unchanged, which the design names as a goal.
- A new chat platform only changes the hook's mapping table, never the formatter.
- Cost: one more mapping layer in `hook.py`, and the scaffold's stub and its test were replaced.
