# 0005. Log hook failures with the traceback, never the reply

Status: Accepted
Issue: #10

## Context

The hook spec said a failed rewrite logs one warning with the exception type only, "no traceback with locals", so reply text never reaches the logs. Hermes's contributing rules say a broad `except Exception` that logs must keep the traceback (`exc_info=True` or `logger.exception`), or carry a `# health: allow` waiver. Without a traceback, a formatter bug reported by a user cannot be located.

## Decision

The hook catches every exception and logs one `WARNING` with `exc_info=True`: `lyre: rewrite skipped (<ExceptionType>) turn=<turn_id>`.

- Python's standard traceback lists file names, line numbers and source lines, not local variables, so the reply text is not in it.
- The formatter never puts reply text into an exception message: its messages name the bad option or the rule that broke a contract (`an inline rule produced a newline`). A test feeds a reply with a marker string through a raising formatter and checks the log holds neither the marker nor the reply.
- The formatter catches its own failures and returns the input (its fail-open contract), so the hook could not see them. `format_for_speech` takes an optional keyword-only `on_error` callback, called inside its `except` block; the hook passes one that logs the same warning. The formatter itself still does no I/O.
- The hook spec's error table is updated to match.

## Consequences

- Formatter bugs are diagnosable from a user's log.
- If a future exception message includes reply text, it would reach the log; the marker test catches that for the paths it covers, and review must keep exception messages free of input text.
