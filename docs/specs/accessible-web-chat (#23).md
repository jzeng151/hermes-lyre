# Accessible Web Chat Spec

Issue: #23 (stretch)
Design: [DESIGN.md](../../DESIGN.md)
Owner: @jzeng151
Status: Draft

## Goal

A screen-reader user can chat with Hermes from a web dashboard tab built from plain, semantic HTML: type in a labeled text box, hear each reply announced once it is complete, and review the conversation with ordinary screen-reader navigation.

## Non-goals

- No changes to the built-in dashboard chat or any built-in page (`tab.override` is not used).
- No Desktop app UI.
- No streaming display. The reply appears once, complete.
- No file upload, images, voice or tool-approval UI.
- No custom theme or visual design beyond readable defaults that follow the active dashboard theme.

## Contract

### Plugin parts

```
lyre/dashboard/
  manifest.json      tab: {path: "/lyre-chat", position: "end"}, label "Accessible chat", api: "plugin_api.py"
  dist/index.js      pre-built IIFE bundle using window.__HERMES_PLUGIN_SDK__ (React from the SDK)
  plugin_api.py      FastAPI router mounted at /api/plugins/lyre/
```

### Backend routes

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `POST` | `/api/plugins/lyre/messages` | `{"session_id": str or null, "text": str}` | `{"session_id": str, "reply": str}` |
| `GET` | `/api/plugins/lyre/sessions/{session_id}` | none | `{"messages": [{"role": "user" or "assistant", "text": str}]}` |

- `text` is 1 to 20,000 characters; otherwise `400 {"code": "invalid_text", "message": "..."}`.
- Replies are passed through `format_for_speech` with the `markdown` profile and the user's verbosity.
- Errors return `{"code": str, "message": str}` with a plain-sentence message the UI reads out.

How the route starts an agent turn is **open question Q1**.

### Page structure

- One `h1`: "Accessible chat".
- A `main` landmark containing the conversation as an ordered list, each message an `article` with a heading level 2 ("You said", "Hermes replied").
- A `form` with a `label` for the text box, a multi-line `textarea`, and a "Send" button. Enter adds a new line; Ctrl+Enter or the button sends.
- An `aria-live="polite"` region that receives the finished reply text once, and "Hermes is working" while waiting.
- Focus stays in the text box after sending. No focus traps. Every control reachable by keyboard.
- Errors go to an `role="alert"` element.

## Acceptance Criteria

- [ ] **AC-1** Given NVDA or VoiceOver on the tab, when the user sends a message, then "Hermes is working" is announced and then the complete reply is announced once.
- [ ] **AC-2** Given a conversation of five turns, when the user navigates by heading, then each message is reachable and labeled with who said it.
- [ ] **AC-3** Given keyboard only, when the user sends, reads and sends again, then no mouse is needed and focus never leaves the page.
- [ ] **AC-4** Given an empty message, when the user sends, then an error is announced and nothing is sent.
- [ ] **AC-5** Given an automated accessibility checker (axe), when the page is scanned, then it reports no serious or critical issues.
- [ ] **AC-6** Given the dashboard's auth gate, when the API is called without a dashboard session, then it is refused.

## Edge Cases

- **Empty input:** rejected client and server side.
- **Duplicates:** a double-clicked Send sends once (button disabled while waiting).
- **Concurrency:** one turn at a time per page; a second send while waiting is refused with an announced message.
- **Long replies:** announced once; the full text is in the message list for review.
- **Permissions:** routes inherit the dashboard's authentication; no route works without it.

## Open Questions

- [ ] **Q1** Which supported API lets a dashboard plugin route run an agent turn in a session and wait for the final reply? Without one, this feature is blocked. Check the dashboard and plugin docs at v0.23.0.
- [ ] **Q2** Does the reply reach the route already rewritten by Lyre's hook (platform value of that session), or should the route format it itself? Avoid formatting twice.
- [ ] **Q3** Does the catalog require any capability declaration or review rule for a dashboard bundle and backend router?
- [ ] **Q4** Which dashboard theme variables are safe to use for readable contrast?

## Output / Deliverables

- Code: `lyre/dashboard/` folder only.
- Tests: route tests with a fake agent turn; manual screen-reader and axe checks.
- Rollback: remove the `dashboard/` folder or disable the plugin; no stored data of its own.
