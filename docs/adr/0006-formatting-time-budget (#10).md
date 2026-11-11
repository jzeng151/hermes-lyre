# 0006. Raise the 20 KB formatting budget on CI to 100 ms

Status: Accepted
Issue: #10, #3

## Context

The design set a budget of under 50 ms for formatting a 20 KB reply, checked by a CI test that times one call on a reply mixing every rule. The review rounds added protection for many rare inputs (code and math inside lists and quotes, link targets, HTML attributes, table cells). Each check is small, but together they brought the test reply to about 29 ms on a desktop and 50 to 57 ms on GitHub's hosted runners, so the test failed on every runner.

Profiling shows no single hotspot. Block segmentation, span protection, table checks, quote processing and the inline rules each take a few milliseconds, and the test reply repeats an emoji, a quote, a table and a list about 170 times, so every path runs often. Cutting about 40% would mean restructuring the pipeline, for example segmenting once instead of twice. That is too risky to do without its own review.

## Decision

The budget for a 20 KB reply is under 100 ms on CI hardware. The hook's AC-8 and the formatter's AC-9 use that number, and the CI test asserts it.

- A reply is read by a person after a model has spent seconds producing it, so a 100 ms rewrite is not noticeable.
- Replies over 200,000 bytes are still skipped in under 5 ms (formatter AC-8), so the worst case stays bounded.
- The test still measures one call after a warm-up, so a real slowdown, such as a quadratic path, still fails it.

## Consequences

- CI passes with headroom on slower runners.
- About half the old budget is used on a desktop and most of the new one on CI, so a further large slowdown fails the test. Making the pipeline faster (one segmentation pass, cheaper table checks) remains worth doing, and the budget can return to 50 ms once a measured change gets there.
