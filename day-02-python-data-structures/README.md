# Day 2 — Python Data Structures (the wrong container is a silent slowdown)

**Topic from the series:** "The wrong container is a silent slowdown" —
lists vs sets vs dicts vs tuples; the cost of asking the wrong
question of your data.

**The one everyday analogy:** searching a shelf slot by slot vs asking
the magic bag. A bouncer checking a photo album page-by-page vs typing
a name into the guest-list app — the line moves at the same speed at
2 AM as at 9 PM.

**The one-line lesson:** match the container to the question — order?
list. "Seen this?" set. Labels? dict. Fixed record? tuple. And when
the set won't fit in memory, trade exactness for a Bloom filter's
fixed-size blur.

## Today's 5 problems

| # | Problem | Concept drilled |
|---|---------|----------------|
| 1 | The dedup job that gets slower every day | Set membership O(1) vs list scan O(n) |
| 2 | The dedup keys that wouldn't freeze | Freezing unhashable values into set keys |
| 3 | The join that scanned the shelf | Dict-index hash join vs nested loops |
| 4 | The cache key that couldn't hold its shape | Canonical hashable cache keys |
| 5 | The 500M users that wouldn't fit | Bloom filter with optimal sizing |

Run them: `python -m pytest tests -q` from this folder.
