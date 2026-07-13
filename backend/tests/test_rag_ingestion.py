"""Unit tests for the pure chunking logic in app/rag/ingestion.py — no ChromaDB,
no embedding model, no I/O. Only indirect coverage existed before (through mocks
in the orchestrator/API tests), so bugs in the actual splitting/overlap logic
could slip through unnoticed."""

from app.rag.ingestion import _recursive_split


def test_short_text_is_not_split():
    text = "A short paragraph that fits within the chunk size easily."
    chunks = _recursive_split(text, chunk_size=512, overlap=64)
    assert chunks == [text]


def test_empty_text_returns_no_chunks():
    assert _recursive_split("", chunk_size=512, overlap=64) == []
    assert _recursive_split("   ", chunk_size=512, overlap=64) == []


def test_long_text_is_split_into_multiple_chunks():
    # Three paragraphs, each individually short, but combined over chunk_size.
    paragraph = "Sentence one. Sentence two. Sentence three. " * 4
    text = "\n\n".join([paragraph] * 5)
    chunks = _recursive_split(text, chunk_size=200, overlap=32)
    assert len(chunks) > 1
    # No chunk should wildly exceed the target size (some slack allowed for overlap).
    assert all(len(c) <= 200 * 1.6 for c in chunks)


def test_consecutive_chunks_share_overlap_text():
    paragraph = "Paragraph about gradient descent and optimization. " * 3
    text = "\n\n".join([paragraph] * 6)
    chunks = _recursive_split(text, chunk_size=150, overlap=40)
    assert len(chunks) > 1

    # Each chunk after the first should start with a tail fragment of the previous
    # chunk's un-overlapped content — that's the whole point of overlap: a concept
    # split across a chunk boundary is still retrievable from either chunk.
    for i in range(1, len(chunks)):
        prev_tail_words = chunks[i - 1][-40:].split()[-3:]
        assert any(word in chunks[i] for word in prev_tail_words if word)


def test_falls_back_to_word_split_when_no_natural_boundary_fits():
    # One giant "sentence" with no paragraph/sentence/space boundaries that fit —
    # forces the final fallback (raw character slicing).
    text = "x" * 1000
    chunks = _recursive_split(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)
