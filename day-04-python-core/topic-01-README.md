# Day 4 — Topic 1: Python Foundations (textbook Chapters 1–2)

Variables, data types, operators, conditionals, loops, and the Python
execution model — taught through the hardest realistic data-engineering
versions of each idea, not as a syntax survey. Every problem opens with
a beginner foothold, climbs to a production breakage, and closes with
one everyday analogy.

## The 5 problems

| # | File | Concept | Production story |
|---|------|---------|------------------|
| 1 | `problem_01_foundations_type_coercion.py` | Variables, data types, type conversion | `coerce_row` / `coerce_batch`: a revenue CSV where every cell is a string — `bool("False")` is `True`, `int("12.5")` raises, `"$1,234.56"` needs cleaning. Bad cells become logged errors; the batch never dies on one row. |
| 2 | `problem_02_foundations_short_circuit.py` | Operators, `and`/`or` short-circuiting | `make_settlement_filter` + `safe_float` + `with_default` + `all_of`/`any_of`: guard clauses before dangerous calls, `or`-defaults that must not eat real `0`s, combinators that truly short-circuit expensive checks. |
| 3 | `problem_03_foundations_validation_branching.py` | Conditionals, exhaustive branching | `classify_row` stamps every inbound transaction `ACCEPT` / `QUARANTINE` / `REJECT`: cheapest checks first, `is None` instead of truthiness (so `0.0` is zero, not missing), no input falls through the chain. |
| 4 | `problem_04_foundations_chunked_loops.py` | Loops, iterators, `break`/`continue`/`for...else` | `stream_totals`: per-currency tallies over a multi-GB log in fixed-size chunks via `itertools.islice` — flat memory, poison-pill `break` with an honest `completed: False` report, malformed lines skipped and counted. |
| 5 | `problem_05_foundations_identity_mutability.py` | Execution model: names, `is` vs `==`, mutability | `register_tenant` / `make_default_config` / `dedupe_rows`: per-tenant configs that can never alias shared defaults (deep copies, fresh objects per call), `is None` guards, equality-vs-identity dedup. |

## Run the tests

```bash
cd ~/workspace/360-day-data-engineering-problems/day-04-python-core
python -m pytest tests/test_topic1_foundations.py -q
```

19 tests, all green. Each problem file also runs standalone with
`python problem_0X_foundations_*.py` for a worked demo.
