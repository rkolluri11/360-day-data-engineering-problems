# Day 5 — Strings & Data Parsing (where pipelines go to die)

**Topic from the series:** "Strings look easy. That's exactly why they
kill pipelines." — strip/split/join, f-strings, regex vs str methods,
encodings, and streaming validation. The unglamorous skill every
working pipeline stands on.

**The one everyday analogy:** proofreading a contract — everything reads
fine until one misplaced comma costs millions. Punctuation does double
duty (separating *and* sitting inside), quotes are the escape hatch, and
invisible characters are the typos you can't see until "show invisibles"
is on.

**The one-line lesson:** parse defensively — respect quotes, clean the
invisible, decode without crashing, and validate every row's shape at
the source. The wandering column must never travel quietly.

## Today's 5 problems

| # | Problem | Concept drilled |
|---|---------|----------------|
| 1 | The field that ate the delimiter | Quote-aware splitting, escaped quotes, fail-fast on unbalanced quotes |
| 2 | The log line with three faces | Compiled regex for structure, str-method pre-filters for speed |
| 3 | The clean field that wasn't | Invisible Unicode (zero-width, BOM, soft hyphen, nbsp) removal |
| 4 | The bytes that lied about being text | errors="replace" decoding, mojibake heuristics |
| 5 | The 10 GB log that wouldn't fit | Generator streaming + per-row column-count validation |

Run them: `python -m pytest tests -q` from this folder.
