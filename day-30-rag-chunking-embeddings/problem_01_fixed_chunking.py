"""Day 30 - Problem 1: fixed-size chunking — the naive baseline every RAG
pipeline starts from (and outgrows).

A language model cannot swallow a whole 200-page manual in one prompt,
so long text is cut into chunks before embedding. The simplest cut is
fixed-size: every ``size`` characters, no questions asked.

Beginner foothold: it is slicing bread with a ruler. ``text[i:i+size]``
for i = 0, size, 2*size... The last slice may be shorter; an empty
document yields no chunks at all.

The flaw this problem exists to show: a fixed cut splits mid-word and
mid-sentence, so the chunk "…the quarterly revenue grew by 12" loses
the "%" — and the meaning — to the next chunk. Problems 2 and 3 fix
exactly this.
"""

from __future__ import annotations


def chunk_fixed(text: str, size: int) -> list[str]:
    """Split ``text`` into consecutive chunks of at most ``size`` chars.

    Raises ValueError for a non-positive size. Empty text returns [].
    """
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


if __name__ == "__main__":
    doc = "Revenue grew 12% this quarter. Costs fell 3% on lower cloud spend."
    for i, chunk in enumerate(chunk_fixed(doc, 20)):
        print(f"chunk {i}: {chunk!r}")
