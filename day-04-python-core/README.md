# Day 4 — Python Core: the first 4 textbook topics, 20 problems

**What today is:** a textbook reset. Days 1–3 went deep on one idea
each; Day 4 covers the first 4 topics of standard Python textbooks in
order — the foundations every data pipeline is built on — with 5
production-grade problems per topic.

**The one everyday analogy:** the foundation, walls, wiring, and
plumbing of a house. Skip one and the house looks fine — until the
first storm. Each topic below is one of those four; the problems are
the storms.

**The one-line lesson:** master the boring parts and the exciting
parts stop breaking at 2 AM.

## The 4 topics × 5 problems

### Topic 1 — Python Foundations
Variables, data types, operators, conditionals, loops, execution model.

| # | Problem | Concept drilled |
|---|---------|----------------|
| 1 | The revenue CSV that lied about its types | Type coercion: `bool("False")` is `True`, cleaning `"$1,234.56"` |
| 2 | The filter that called the expensive API anyway | Short-circuit evaluation, guard clauses, `or`-defaults that must not eat `0` |
| 3 | The transaction that fell through every check | Conditional branching: cheapest checks first, `is None` vs truthiness |
| 4 | The 2 GB log that wouldn't fit in RAM | Chunked streaming loops, `islice`, poison-pill `break`, `for...else` |
| 5 | The tenant config that shared a brain | Identity vs equality, mutable aliasing, per-tenant isolation |

### Topic 2 — Data Structures
Lists, tuples, sets, dictionaries, mutability.

| # | Problem | Concept drilled |
|---|---------|----------------|
| 6 | The dedup that took minutes instead of 0.05s | List-vs-set dedup at 200k scale, order-preserving |
| 7 | The enrichment join that scanned for 6 hours | Dict O(1) lookup index, missing keys stamped `UNKNOWN` |
| 8 | The partition key that couldn't be hashed | Tuple immutability for composite keys |
| 9 | The error report haunted by last Tuesday | Mutable-default trap, `errors=None` idiom, never mutating inputs |
| 10 | The rollup with the impossible `KeyError` chain | Nested group-by aggregation with `setdefault` |

### Topic 3 — Functions
Arguments, `*args`/`**kwargs`, scope, lambda, higher-order functions.

| # | Problem | Concept drilled |
|---|---------|----------------|
| 11 | The dispatcher that had to learn every signature | `*args`/`**kwargs` forwarding, signature inspection |
| 12 | The audit log that remembered everything, forever | Mutable-default trap in long-running workers, `None`-sentinel |
| 13 | The validators that all checked the wrong column | Late binding in loop-created closures, factory fix |
| 14 | The filter rules rewritten for every report | Lambdas + higher-order `all_of`/`any_of`, config-driven predicates |
| 15 | The FX step that passed Monday and failed Friday | Global scope vs pure functions, `(converted, errors)` returns |

### Topic 4 — Pythonic Programming
Comprehensions, `enumerate`, `zip`, `map`/`filter`, `any`/`all`, generators.

| # | Problem | Concept drilled |
|---|---------|----------------|
| 16 | The job that read 40M events twice | List comprehension: filter + transform in one pass |
| 17 | The enrichment that scanned per order for 6h | Dict comprehension building a latest-record index |
| 18 | The meter feed that silently lost a row | `zip(strict=True)` + `enumerate` for aligned merging |
| 19 | The quality gate that answered 20 minutes late | `any`/`all` short-circuiting over lazy generators |
| 20 | The 20 GB file that needed 60 GB of RAM | Generator-expression pipelines, one-line peak memory |

Run them: `python -m pytest tests -q` from this folder — 71 tests, all green.
