"""Day 30 tests: chunking and embeddings for RAG (Python finale)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_fixed_chunking import chunk_fixed
from problem_02_overlap_chunking import chunk_overlap
from problem_03_recursive_chunking import chunk_recursive
from problem_04_embeddings_search import cosine_similarity, embed, search
from problem_05_retrieval_guard import Retriever


# --- Problem 1: fixed chunking ---
def test_fixed_slices_and_last_short():
    assert chunk_fixed("abcdefghij", 3) == ["abc", "def", "ghi", "j"]


def test_fixed_empty_and_bad_size():
    import pytest

    assert chunk_fixed("", 5) == []
    with pytest.raises(ValueError):
        chunk_fixed("abc", 0)


def test_fixed_reconstructs():
    doc = "Revenue grew 12% this quarter."
    assert "".join(chunk_fixed(doc, 7)) == doc


# --- Problem 2: overlap chunking ---
def test_overlap_windows_share_tail():
    chunks = chunk_overlap("abcdefghij", 4, 2)
    assert chunks == ["abcd", "cdef", "efgh", "ghij", "ij"]


def test_overlap_short_doc_single_chunk():
    assert chunk_overlap("abc", 10, 3) == ["abc"]


def test_overlap_rejects_bad_params():
    import pytest

    with pytest.raises(ValueError):
        chunk_overlap("abc", 0, 0)
    with pytest.raises(ValueError):
        chunk_overlap("abc", 4, 4)  # overlap must be < size
    with pytest.raises(ValueError):
        chunk_overlap("abc", 4, -1)


def test_overlap_no_empty_trailing():
    chunks = chunk_overlap("abcdef", 4, 1)
    assert chunks and all(chunks)
    assert chunks[-1] == "f" or len(chunks[-1]) > 0


# --- Problem 3: recursive chunking ---
def test_recursive_keeps_paragraphs_whole():
    doc = "Short para one.\n\nShort para two."
    assert chunk_recursive(doc, 40) == ["Short para one.", "Short para two."]


def test_recursive_never_exceeds_max():
    doc = (
        "Revenue grew 12% this quarter. Costs fell 3% on lower cloud spend. "
        "The data team shipped a new pipeline that cut reporting latency in half."
    )
    chunks = chunk_recursive(doc, 30)
    assert chunks and all(len(c) <= 30 for c in chunks)


def test_recursive_splits_long_sentence_on_words_not_chars():
    doc = "Alpha beta gamma delta epsilon zeta eta theta."
    chunks = chunk_recursive(doc, 20)
    assert chunks and all(len(c) <= 20 for c in chunks)
    # No chunk should end mid-word unless a single word forced it.
    assert all(not c.endswith(" ") for c in chunks)


def test_recursive_empty_and_bad_size():
    import pytest

    assert chunk_recursive("   ", 10) == []
    with pytest.raises(ValueError):
        chunk_recursive("abc", 0)


# --- Problem 4: embeddings + search ---
def test_embed_deterministic_and_normalized():
    import math

    a = embed("revenue grew this quarter")
    b = embed("revenue grew this quarter")
    assert a == b  # same text, same vector, every run
    assert abs(math.sqrt(sum(v * v for v in a)) - 1.0) < 1e-9


def test_embed_empty_is_zero_vector():
    assert embed("") == [0.0] * 64
    assert cosine_similarity(embed(""), embed("revenue")) == 0.0


def test_cosine_identical_is_one_unrelated_is_zero():
    assert cosine_similarity(embed("revenue growth"), embed("revenue growth")) == 1.0
    assert cosine_similarity(embed("aaaa bbbb"), embed("cccc dddd")) == 0.0


def test_search_ranks_best_first_and_excludes_zero():
    docs = [
        "Revenue grew 12% this quarter.",
        "The data team shipped a new pipeline.",
        "Costs fell 3% on lower cloud spend.",
    ]
    results = search("quarterly revenue growth", docs, top_k=2)
    assert results[0][0] == 0  # revenue doc ranks first
    assert len(results) <= 2
    assert all(score > 0 for _, score in results)


def test_search_empty_query_and_bad_top_k():
    import pytest

    assert search("", ["revenue"], top_k=3) == []
    with pytest.raises(ValueError):
        search("revenue", ["revenue"], top_k=0)


# --- Problem 5: retrieval guard ---
def test_retriever_threshold_drops_weak_matches():
    retriever = Retriever()
    retriever.add("Revenue grew 12% this quarter.", source="report.pdf")
    retriever.add("The data team shipped a new pipeline.", source="notes.md")
    # A high threshold admits only the strong revenue match.
    results = retriever.query("revenue grew this quarter", top_k=5, min_score=0.5)
    assert len(results) == 1
    assert results[0].source == "report.pdf"


def test_retriever_dedupes_identical_text():
    retriever = Retriever()
    retriever.add("Revenue grew 12% this quarter.", source="a.pdf")
    retriever.add("Revenue grew 12% this quarter.", source="b.pdf")
    results = retriever.query("revenue growth", top_k=5)
    assert len(results) == 1  # same text counted once


def test_retriever_top_k_caps_and_empty_cases():
    retriever = Retriever()
    for i in range(5):
        retriever.add(f"revenue report number {i}", source=f"doc{i}.pdf")
    assert len(retriever.query("revenue", top_k=2)) == 2
    assert Retriever().query("revenue") == []  # empty index
    assert retriever.query("   ") == []  # empty query


def test_retriever_rejects_bad_params():
    import pytest

    retriever = Retriever()
    with pytest.raises(ValueError):
        retriever.query("revenue", top_k=0)
    with pytest.raises(ValueError):
        retriever.query("revenue", min_score=1.5)
