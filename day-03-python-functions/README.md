# Day 3 — Python Functions (the recipe card with blanks)

**Topic from the series:** "The recipe card with blanks" —
arguments, `*args`/`**kwargs`, scope, lambda, higher-order
functions. Where the pipeline's behavior is actually decided.

**The one everyday analogy:** a recipe card with blanks to fill in.
Positional arguments are shouted across the counter in order — add
one item in the middle and the cook hears it as the side dish.
Keyword arguments are labeled lines on the ticket — new lines never
shift the old ones. `*args`/`**kwargs` are the "and whatever else"
line at the bottom; keyword-only arguments are the lines in bold
that can't be misread.

**The one-line lesson:** push decisions to the call site — keyword-only
config, `*args`/`**kwargs` forwarded untouched, small functions composed.
A growing pipeline should never silently re-plumb itself.

## Today's 5 problems

| # | Problem | Concept drilled |
|---|---------|----------------|
| 1 | The step that broke when the signature grew | Keyword-only args + signature-inspecting dispatch |
| 2 | The retry wrapper that ate the arguments | Decorator factories, functools.wraps, *args/**kwargs forwarding |
| 3 | The sort key that died on one bad row | Higher-order key builders, lambdas that survive messy data |
| 4 | The tenant config that leaked | Closures/partial config binding with true isolation |
| 5 | The pipeline made of functions | Function composition with error attribution |

Run them: `python -m pytest tests -q` from this folder.
