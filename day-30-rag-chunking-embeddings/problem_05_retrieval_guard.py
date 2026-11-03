"""Day 30 - Problem 5: the retrieval pipeline guard — the piece that stops
RAG from confidently answering with the wrong context.

Problems 1–4 are parts. A production retriever composes them and adds
guards, because raw top-k similarity has three failure modes a demo
never shows: weak matches that should have been "I don't know",
duplicate chunks (the same paragraph embedded twice) crowding out real
variety, and unbounded result sets flooding the prompt.

Beginner foothold: the retriever is a bouncer with a guest list. The
similarity score is the ID check (``min_score`` — below it, no entry).
Dedup is the "one wristband per person" rule (same text twice keeps
only its best score). ``top_k`` is the room capacity. An empty query
or an empty index returns no results — never an error, never a guess.

Results carry their source metadata through untouched, so the answer
can cite where each chunk came from.
"""

from __future__ import annotations

from problem_04_embeddings_search import cosine_similarity, embed


class RetrievalResult:
    """One retrieved chunk: its text, score, and source metadata."""

    def __init__(self, text: str, score: float, source: str) -> None:
        self.text = text
        self.score = score
        self.source = source

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return f"RetrievalResult(score={self.score:.3f}, source={self.source!r})"


class Retriever:
    """In-memory chunk index with threshold, dedup, and top-k guards."""

    def __init__(self, dim: int = 64) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim
        self._chunks: list[tuple[str, str, list[float]]] = []

    def add(self, text: str, source: str) -> None:
        """Index one chunk with its source label."""
        self._chunks.append((text, source, embed(text, self.dim)))

    def query(self, query_text: str, top_k: int = 3, min_score: float = 0.0) -> list[RetrievalResult]:
        """Retrieve up to ``top_k`` chunks for ``query_text``.

        Drops matches below ``min_score``, dedupes identical chunk
        text (keeping the best score), and sorts best first. Empty
        queries and empty indexes return []. Raises ValueError for a
        non-positive ``top_k`` or a ``min_score`` outside [0, 1].
        """
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be within [0, 1]")
        if not query_text.strip() or not self._chunks:
            return []
        query_vec = embed(query_text, self.dim)
        best_by_text: dict[str, RetrievalResult] = {}
        for text, source, vec in self._chunks:
            score = cosine_similarity(query_vec, vec)
            if score < min_score or score <= 0:
                continue
            current = best_by_text.get(text)
            if current is None or score > current.score:
                best_by_text[text] = RetrievalResult(text, score, source)
        ranked = sorted(best_by_text.values(), key=lambda r: -r.score)
        return ranked[:top_k]


if __name__ == "__main__":
    retriever = Retriever()
    retriever.add("Revenue grew 12% this quarter.", source="q3-report.pdf")
    retriever.add("Revenue grew 12% this quarter.", source="q3-report.pdf")  # dup
    retriever.add("Costs fell 3% on lower cloud spend.", source="q3-report.pdf")
    retriever.add("The data team shipped a new pipeline.", source="eng-notes.md")
    for result in retriever.query("quarterly revenue growth", top_k=2, min_score=0.1):
        print(f"{result} :: {result.text}")
