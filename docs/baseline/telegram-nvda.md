# Baseline transcript: Telegram with NVDA (#2)

- Client: Telegram Desktop for Windows. NVDA's browse-mode phrases ("document", "same page link") appear in the capture.
- Screen reader: NVDA 2026.3.1, oneCore voice, default speech and punctuation settings
- OS: Windows 11 25H2
- Lyre: off
- Sent with: `hermes send --to telegram --file docs/baseline/test-reply.md` (Telegram adapter, MarkdownV2 path, rich messages off)
- Captured from: NVDA Speech Viewer, read with Say All

Speech Viewer shows the text handed to the voice, not how punctuation was pronounced. Symbols such as `\`, `├──` and `-` appear here whether or not they were spoken; the listening checks at the end record what was heard.

Surrounding chat UI and other messages are trimmed. Whitespace is as captured.

## Transcript

```text
Deploy check for   edit    api-gateway  
  Unlabeled graphic    ✅   Unit tests passed
  Unlabeled graphic    ❌   Integration tests failed

Unlabeled graphic    ⚠️   2 warnings in the build log
  Unlabeled graphic    🚀   Ready to retry once the fix lands
  The failure is in   auth refresh  : the token cache returns an expired entry when the clock skews by more than   30 seconds  .   Run   edit    npm test -- --grep refresh   to reproduce it. 
Note the literal asterisk in the config key   edit    retry\*limit  , which is escaped on purpose.

api-gateway  
  • Region: us-east-1
  • Status:   Unlabeled graphic    ✅   healthy
  • Latency: 42 ms
  auth  
  • Region: us-east-1
  • Status:   Unlabeled graphic    ❌   failing
  • Latency: 1,204 ms

billing  
  • Region: eu-west-1
  • Status:   Unlabeled graphic    ✅   healthy
  • Latency: 88 ms
  search  
  • Region: eu-west-1
  • Status:   Unlabeled graphic    ⚠️   degraded
  • Latency: 512 ms

notifications  
  • Region: ap-south-1
  • Status:   Unlabeled graphic    ✅   healthy
  • Latency: 61 ms
  uploads  
  • Region: ap-south-1
  • Status:   Unlabeled graphic    ✅   healthy
  • Latency: 97 ms

reports  
  • Region: us-west-2
  • Status:   Unlabeled graphic    ⚠️   degraded
  • Latency: 430 ms
  webhooks  
  • Region: us-west-2
  • Status:   Unlabeled graphic    ✅   healthy
  • Latency: 55 ms

ledger  
  • Region: ca-central-1
  • Status:   Unlabeled graphic    ❌   failing
  • Latency: 2,310 ms
  Python
def summarize(results):
      # ✅ marks a pass, ❌ marks a failure
      passed = [r for r in results if r.ok]

    print(f"**{len(passed)}** of {len(results)} passed ✅")
      return "| name | ok |" if passed else "⚠️ none"



Next steps:
  1. 
Fix the cache
     - Compare expiry against server time
       - Fall back to a fresh token on mismatch
     - Add a skew test
  2. 
Re-run the deploy
     - Watch the ledger service first
  Project layout:
  src/
  ├── auth/
  │   ├──   link    cache.py  
  │   └──   link    refresh.py  
  └── ledger/

    └──   link    client.py  
  Full build log:   link    build-4821.log  
  Dashboard:   link    https://status.example.com/services/auth?
link    window=24h&view=latency  03:12 PM
```

## Observations

- **Formatting breaks the flow.** Bold, italic and inline code are separate runs. NVDA pauses before and after each one, as if at a full stop (reported by ear).
- **Inline code is announced as "edit"**, a text-field role, before its text. Nothing says it is code. The backticks themselves are not spoken: Telegram displays the span as code.
- **Status emoji are "Unlabeled graphic" plus the emoji** (in prose and table cells; not inside the code block).
- **Heading:** the `##` is not spoken. Nothing marks the line as a heading.
- **Table:** Telegram's adapter turned it into bullet groups (name line, then `• Region`, `• Status`, `• Latency`). All 9 rows survive and the ledger row (row 9) is findable.
- **Code block:** displayed as a block. Telegram adds its own `Python` label; the fences are not spoken and there is no end marker. Contents are passed through literally, including `**`, `|` and emoji.
- **Nested list:** numbered items put the number and the text on separate lines. Sub-items keep a literal `-` marker.
- **Folder tree:** the box-drawing characters are in the text sent to the voice but are not spoken (see below). `cache.py`, `refresh.py` and `client.py` are auto-linked by Telegram (`.py` is a top-level domain).
- **Markdown link:** only the label (`build-4821.log`) is spoken; the signed URL is hidden behind it.
- **Bare URL:** read as two link pieces split at `?`, possibly where the line wraps.
- **Message end:** the timestamp is read straight after the last link, with no pause.

## Listening checks

- Backslash: not spoken. `retry\*limit` is heard as "retry star limit". The backslash was displayed (it sits inside inline code), so NVDA skips it at the default punctuation level.
- Box-drawing characters (`├──`, `│`, `└──`): not spoken. The tree is heard as the bare names.
- The `-` before list sub-items: not spoken.
- Emoji: hovering an emoji with the mouse reads its name (✅ is "check mark button"). Not confirmed whether Say All speaks the name after "Unlabeled graphic".

## Answers for the formatter spec

- **Q1 (code fences):** not spoken on Telegram, which shows code as a block. NVDA does not say that a code block starts or ends; it reads Telegram's `Python` label and the contents. Keeping fences costs Telegram listeners nothing, and Lyre's labels are the only spoken boundary.
- **Q5 (backticks and backslashes):** NVDA speaks neither at its default punctuation level, in code or in prose (confirmed with `docs/baseline/probe-escapes.md`). The backticks are consumed by Telegram's code display; the cost of keeping them is the "edit" role and the pauses around the code.
- **Q6 (box-drawing characters):** not spoken by NVDA. Unchanged tree lines are safe.
- TalkBack results: `docs/baseline/telegram-talkback.md`. Not tested: VoiceOver, WhatsApp and plain-text clients (Signal, SMS, iMessage).
