# Day 4 — Topic 4: Pythonic Programming

Textbook track: comprehensions, `enumerate`, `zip`, `map`/`filter`, `any`/`all`,
generator expressions. Each problem shows the BEFORE (loop version) vs the AFTER
(Pythonic version) and teaches through the hardest realistic data-engineering
failure, ladder style: beginner foothold first, then the production breakage.

## Problems

| # | File | Concept | Production story |
|---|------|---------|------------------|
| 16 | `problem_16_pythonic_transform_filter.py` | List comprehension: transform + filter in one pass | Nightly job parsed 40M order events with two passes (filter, then transform) — 2x time, 2x memory. `parse_orders()` does both in a single comprehension. |
| 17 | `problem_17_pythonic_index_build.py` | Dict comprehension: build a lookup index | Enrichment scanned the whole address history per order (O(n·m), killed after 6h). `build_latest_index()` builds a `{customer_id → latest record}` index once; enrichment becomes O(1) lookups. |
| 18 | `problem_18_pythonic_merge_aligned.py` | `enumerate` + `zip(strict=True)` | Meter API dropped one reading; plain `zip` silently truncated 500 rows to 499 and the peak row vanished. `merge_feeds()` raises on length mismatch and numbers rows with `enumerate`. |
| 19 | `problem_19_pythonic_quality_gates.py` | `any` / `all` short-circuiting gates | Gate materialized 10M booleans, then answered a yes/no question 20 minutes late. `partition_ready()` short-circuits on the first violation over a generator — corrupt row 12 stops the scan. |
| 20 | `problem_20_pythonic_genexpr_pipeline.py` | Generator expressions: streaming pipelines | 20 GB JSONL needed 3x its size in RAM to compute one number; OOM-killed at 8 GB. `daily_settled_volume()` chains generator expressions — peak memory is one line + one dict. Includes the single-use generator gotcha. |

## Run

```bash
cd day-04-python-core
python -m pytest tests/ -q
```

20 tests in `tests/test_topic4_pythonic.py`, all passing (4–6 per problem:
correctness, equivalence with the loop version, and edge cases).
