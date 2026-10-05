# Day 1 — Python Foundations (the memory-model problem)

**Topic from the series:** "Why a 2 GB file needs 10 GB of RAM" —
Python's execution model, variables, types, loops.

**The one everyday analogy:** reading a book by memorizing the whole
book first vs. reading one page at a time. Python lists do the first
one. Generators do the second.

**The one-line lesson:** Python objects are bigger than they look, and
materializing a dataset turns "bytes on disk" into 4–10× the RAM. The
senior move is streaming: process one item at a time and keep memory
flat no matter how big the input grows.

## Today's 5 problems

| # | Problem | Concept drilled |
|---|---------|----------------|
| 1 | The 2 GB CSV sum | Generators vs lists; lazy iteration |
| 2 | The cache that leaked between functions | Mutable default arguments |
| 3 | The callbacks that all said the last stage | Late-binding closures in loops |
| 4 | The dedup that worked in dev, failed in prod | `is` vs `==`; interning |
| 5 | Group-by under a 5 MB memory budget | Chunking + streaming aggregation |

Run them: `python -m pytest tests -q` from this folder.
