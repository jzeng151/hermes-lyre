❌ **2 tests failed** in `test_auth.py`:

1. `test_login_expired_token`
2. `test_refresh_rotates`

Both fail on the same assertion:

```text
AssertionError: expected 401, got 200
```

The token check is skipped when `DEBUG=1`. Want me to fix it?
