Here's the fix. The loop modified the list while iterating:

```python
items = [x for x in items if x.valid]
for item in items:
    process(item)
```

This builds a new list first, so nothing is skipped.
