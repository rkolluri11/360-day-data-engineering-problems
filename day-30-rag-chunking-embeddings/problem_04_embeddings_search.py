"""Day 30 - Problem 4: embeddings + similarity search — turn words into
numbers, then let geometry answer "which chunk means the same thing?"

A chunk is text; a search engine needs numbers. An embedding maps text
to a fixed-length vector so that similar meanings land close together.
Real systems use neural models; this problem uses a tiny deterministic
stand-in with the same interface, so the retrieval math is identical:
hash each word into one of ``dim`` buckets, count, L2-normalize.

Beginner foothold: think of the vector as a fingerprint of the words
used. Two texts sharing words get vectors pointing the same way, and
cosine similarity — the dot product of normalized vectors — measures
exactly that angle: 1.0 means identical word mix, 0.0 means nothing
in common.

Determinism matters: hashing uses MD5, never Python's salted ``hash``,
so the same text embeds identically in every process, every run.
"""

from __future__ import annotations

import hashlib
import math
import re

_WORD = re.compile(r"\w+")


def embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic bag-of-words embedding, L2-normalized.

    Raises ValueError for a non-positive ``dim``. Empty text (or text
    with no words) returns the zero vector.
    """
    if dim <= 0:
        raise ValueError("dim must be positive")
    vector = [0.0] * dim
    for word in _WORD.findall(text.lower()):
        bucket = int.from_bytes(hashlib.md5(word.encode()).digest()[:8], "little") % dim
        vector[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two vectors (0.0 when either is zero)."""
    if len(a) != len(b):
        raise ValueError("vectors must have equal length")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search(query: str, documents: list[str], top_k: int, dim: int = 64) -> list[tuple[int, float]]:
    """Rank ``documents`` by similarity to ``query``.

    Returns up to ``top_k`` (index, score) pairs, best first, with
    zero-score documents excluded. Raises ValueError for a
    non-positive ``top_k``. An empty query returns [].
    """
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if not query.strip():
        return []
    query_vec = embed(query, dim)
    scored = [
        (i, cosine_similarity(query_vec, embed(doc, dim)))
        for i, doc in enumerate(documents)
    ]
    scored = [(i, s) for i, s in scored if s > 0]
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    return scored[:top_k]


if __name__ == "__main__":
    docs = [
        "Revenue grew 12% this quarter.",
        "The data team shipped a new pipeline.",
        "Costs fell 3% on lower cloud spend.",
    ]
    for index, score in search("quarterly revenue growth", docs, top_k=2):
        print(f"doc {index} (score {score:.3f}): {docs[index]}")
