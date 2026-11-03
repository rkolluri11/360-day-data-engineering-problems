"""Day 30 - Problem 3: recursive chunking — split on structure, not on
character counts.

Overlap (Problem 2) papers over boundary loss but still cuts blindly.
Real RAG chunkers split recursively: try the biggest meaningful unit
first, and only go smaller when a piece still does not fit.

Beginner foothold: it is packing boxes. First try to fit whole
paragraphs. A paragraph that is too big is split into sentences and
the sentences are packed greedily. A sentence that is still too big is
split into words and packed greedily. Only a single word longer than
the limit is hard-cut — the last resort, never the default.

Guarantees: every chunk is at most ``max_size`` characters; no
sentence is split unless it alone exceeds ``max_size``; no word is
split unless it alone exceeds ``max_size``; the chunks, joined in
order, reconstruct the document's sentences (whitespace aside).
"""

from __future__ import annotations

import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(paragraph: str) -> list[str]:
    """Split a paragraph after sentence-ending punctuation."""
    return [s for s in _SENTENCE_SPLIT.split(paragraph.strip()) if s]


def _pack_words(words: list[str], max_size: int) -> list[str]:
    """Greedy-pack words into chunks of at most ``max_size`` chars.

    A single word longer than ``max_size`` is hard-sliced.
    """
    chunks: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_size:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(word), max_size):
                chunks.append(word[i : i + max_size])
            continue
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_size:
            current = candidate
        else:
            chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks


def _pack_pieces(pieces: list[str], max_size: int) -> list[str]:
    """Greedy-pack pieces (sentences) into chunks of at most ``max_size``.

    A piece longer than ``max_size`` is word-packed instead of cut.
    """
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if len(piece) > max_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_pack_words(piece.split(), max_size))
            continue
        candidate = f"{current} {piece}" if current else piece
        if len(candidate) <= max_size:
            current = candidate
        else:
            chunks.append(current)
            current = piece
    if current:
        chunks.append(current)
    return chunks


def chunk_recursive(text: str, max_size: int) -> list[str]:
    """Split ``text`` into chunks of at most ``max_size`` chars,
    respecting paragraph, then sentence, then word boundaries.

    Raises ValueError for a non-positive ``max_size``. Empty or
    whitespace-only text returns [].
    """
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    if not text.strip():
        return []
    chunks: list[str] = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= max_size:
            chunks.append(paragraph)
        else:
            chunks.extend(_pack_pieces(_split_sentences(paragraph), max_size))
    return chunks


if __name__ == "__main__":
    doc = (
        "Revenue grew 12% this quarter. Costs fell 3% on lower cloud spend.\n\n"
        "The data team shipped a new pipeline. It cut reporting latency in half."
    )
    for i, chunk in enumerate(chunk_recursive(doc, 40)):
        print(f"chunk {i}: {chunk!r}")
