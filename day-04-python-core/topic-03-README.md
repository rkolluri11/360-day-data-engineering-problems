# Day 4 — Topic 3: Functions (textbook core)

**Scope:** defining functions, arguments, return values, scope
(local/global/nonlocal), `lambda`, `*args`/`**kwargs`, higher-order
functions, keyword-only args — taught through the hardest realistic
data-engineering failures, not toy examples.

**The one everyday analogy:** functions are order slips in a busy
kitchen. Positional args are shouted in order (one new item in the
middle scrambles everything); keyword args are labeled lines; the
`None`-sentinel is a fresh sheet of paper per order instead of one
shared whiteboard; closures are printed name tags instead of one
shared board everyone points at; pure functions are vending machines
— exact coins in, exact change out.

## The 5 problems (numbered 11–15 across Day 4)

| # | File | Problem | Concept drilled |
|---|------|---------|-----------------|
| 11 | `problem_11_functions_flexible_steps.py` | The dispatcher that had to learn every step's signature | `*args`/`**kwargs` forwarding; plugin-style `run_all` broadcasting shared knobs only to steps that declare them |
| 12 | `problem_12_functions_mutable_default.py` | The audit log that remembered everything, forever | Mutable-default trap; `None`-sentinel for per-call state; weekend OOM in a long-running worker |
| 13 | `problem_13_functions_loop_closures.py` | The validators that all checked the wrong column | Late binding in loop-created closures; factory-function fix for config-driven ETL checks |
| 14 | `problem_14_functions_filter_predicates.py` | The filter rules that had to be rewritten for every report | Lambdas + higher-order `all_of`/`any_of`; config-driven `build_predicate` with audit-ready rule descriptions |
| 15 | `problem_15_functions_pure_scope.py` | The FX step whose tests passed on Monday and failed on Friday | Global-scope spookiness; pure `convert_batch(rows, rate)` + impure shell `run_fx`; deterministic, rerunnable, testable |

Run them: `python -m pytest tests/test_topic3_functions.py -q` from
`day-04-python-core/`. Each file also runs standalone via
`python problem_1X_....py` for the printed walkthrough.
