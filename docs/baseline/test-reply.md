## Deploy check for `api-gateway`

✅ Unit tests passed
❌ Integration tests failed
⚠️ 2 warnings in the build log
🚀 Ready to retry once the fix lands

The failure is in **auth refresh**: the token cache returns an expired entry when the clock skews by more than *30 seconds*. Run `npm test -- --grep refresh` to reproduce it. Note the literal asterisk in the config key `retry\*limit`, which is escaped on purpose.

| Service | Region | Status | Latency |
| --- | --- | --- | --- |
| api-gateway | us-east-1 | ✅ healthy | 42 ms |
| auth | us-east-1 | ❌ failing | 1,204 ms |
| billing | eu-west-1 | ✅ healthy | 88 ms |
| search | eu-west-1 | ⚠️ degraded | 512 ms |
| notifications | ap-south-1 | ✅ healthy | 61 ms |
| uploads | ap-south-1 | ✅ healthy | 97 ms |
| reports | us-west-2 | ⚠️ degraded | 430 ms |
| webhooks | us-west-2 | ✅ healthy | 55 ms |
| ledger | ca-central-1 | ❌ failing | 2,310 ms |

```python
def summarize(results):
    # ✅ marks a pass, ❌ marks a failure
    passed = [r for r in results if r.ok]
    print(f"**{len(passed)}** of {len(results)} passed ✅")
    return "| name | ok |" if passed else "⚠️ none"
```

Next steps:

1. Fix the cache
   - Compare expiry against server time
     - Fall back to a fresh token on mismatch
   - Add a skew test
2. Re-run the deploy
   - Watch the ledger service first

Project layout:

src/
├── auth/
│   ├── cache.py
│   └── refresh.py
└── ledger/
    └── client.py

Full build log: [build-4821.log](https://artifacts.example.com/builds/4821/build.log?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=EXAMPLEKEY%2F20260101%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260101T000000Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef)

Dashboard: https://status.example.com/services/auth?window=24h&view=latency
