# Day 4 — Topic 2: Data Structures (Problems 06–10)

Textbook-standard Python, taught through the hardest realistic
data-engineering problems. Each problem opens with a beginner
foothold, then climbs to the production breakage it prevents.

## Problems

| # | File | What it teaches |
|---|------|-----------------|
| 6 | `problem_06_structures_dedup_scale.py` | **list vs set for dedup.** `dedup_event_ids` keeps first-seen order in O(n) with a set instead of O(n²) with list scans; `find_duplicate_ids` catches double-counted clicks. The silent slowdown that eats the batch SLA. |
| 7 | `problem_07_structures_join_lookup.py` | **dict for O(1) enrichment joins.** `build_lookup` indexes the dimension once; `enrich_facts` left-joins facts with one hash lookup each. Missing keys get an explicit `UNKNOWN` stamp — rows are never silently dropped. |
| 8 | `problem_08_structures_immutable_keys.py` | **tuple immutability for safe keys.** `composite_key` builds hashable ink-not-pencil labels; `group_by_key` groups rows by them. Lists are refused as keys (`TypeError`) and can never drift after filing. |
| 9 | `problem_09_structures_mutability_trap.py` | **The shared-mutable-default trap.** `collect_errors_buggy` leaks batch 1's errors into batch 2; `collect_errors` uses the `errors=None` idiom for a fresh list per call; `merge_context` returns new dicts instead of mutating inputs. |
| 10 | `problem_10_structures_groupby_agg.py` | **Nested structures for group-by.** `revenue_rollup` builds `{region: {currency: {orders, revenue}}}` with `setdefault` so no level can `KeyError`; `top_region_by_revenue` answers the business question straight from the nest. |

## Run

```bash
cd ~/workspace/360-day-data-engineering-problems/day-04-python-core
python -m pytest tests/test_topic2_structures.py -v
```

Each problem file also runs standalone (`python problem_0X_*.py`)
with a small traceable example plus a scale check.
