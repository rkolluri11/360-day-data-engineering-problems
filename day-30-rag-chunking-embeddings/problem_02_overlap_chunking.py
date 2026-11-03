"""Day 30 - Problem 2: overlapping chunks — keep the sentence whole across
the cut.

Problem 1's flaw: a fact straddling a boundary is split in two, and
neither half retrieves well. The standard fix is overlap: each window
shares its tail with the next window's head, so a boundary sentence
appears complete in at least one chunk.

Beginner foothold: it is shingles on a roof. Each shingle covers
``size`` characters, but the next one starts ``overlap`` characters
before the previous one ended — so every boundary is covered twice.
The step between windows is ``size - overlap``.

Rules: overlap must be smaller than size (otherwise the window never
advances); a document shorter than ``size`` is a single chunk; no
empty trailing chunk is ever emitted.
"""

from __future__ import annotations


def chunk_overlap(text: str, size: int, overlap: int) -> list[str]:
    """Split ``text`` into windows of ``size`` chars, each overlapping
    the previous by ``overlap`` chars.

    Raises ValueError for a non-positive size or an overlap outside
    [0, size). Empty text returns [].
    """
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")
    if not text:
        return []
    step = size - overlap
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += step
    return chunks


if __name__ == "__main__":
    doc = "Revenue grew 12% this quarter. Costs fell 3% on lower cloud spend."
    for i, chunk in enumerate(chunk_overlap(doc, 25, 10)):
        print(f"chunk {i}: {chunk!r}")
