### What went wrong

The job hit `MemoryError` at step 3 ❌.

**Likely cause:** the batch size is too large.

**Fix:** set `batch_size: 16` in `config.yaml`, then rerun:

```bash
make train
```
