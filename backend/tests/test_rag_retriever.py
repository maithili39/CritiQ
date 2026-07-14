"""
Unit tests for app/rag/retriever.py's query construction and relevance-scoring/
filtering logic — previously only exercised indirectly through orchestrator mocks
that never touched the real scoring math. ChromaDB and the embedding model are
stubbed so these run without any external dependency.
"""

from unittest.mock import MagicMock

import numpy as np

from app.rag import retriever


def test_build_query_includes_role_skills_topics_and_focus():
    query = retriever._build_query(
        role="ai_ml",
        skills=["PyTorch", "NLP"],
        topics=["Transformers"],
        focus="fundamentals",
    )
    assert "Ai Ml" in query
    assert "PyTorch" in query and "NLP" in query
    assert "Transformers" in query
    assert "fundamentals" in query


def test_build_query_handles_no_skills_or_topics():
    query = retriever._build_query(role="data_science", skills=[], topics=[])
    assert "general concepts" in query
    assert "Topics:" not in query


def _make_fake_collection(distances, documents=None, metadatas=None, count=10):
    n = len(distances)
    documents = documents or [f"chunk {i}" for i in range(n)]
    metadatas = metadatas or [{"source": f"doc{i}.pdf", "page": i} for i in range(n)]

    collection = MagicMock()
    collection.count.return_value = count
    collection.query.return_value = {
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }
    return collection


def test_retrieve_context_filters_out_low_similarity_chunks(monkeypatch):
    # ChromaDB cosine distance: 0=identical, 2=opposite -> similarity = 1 - dist/2.
    # distances [0.0, 0.6, 1.9] -> similarities [1.0, 0.7, 0.05]; min_score=0.25
    # should keep only the first two.
    fake_collection = _make_fake_collection(distances=[0.0, 0.6, 1.9])
    monkeypatch.setattr(retriever, "get_collection", lambda role: fake_collection)
    monkeypatch.setattr(
        retriever, "_get_embedding_model", lambda: MagicMock(encode=lambda texts: np.array([[0.1, 0.2, 0.3]]))
    )

    results = retriever.retrieve_context(role="ai_ml", skills=["PyTorch"], topics=[], min_score=0.25)

    assert len(results) == 2
    assert all(r["score"] >= 0.25 for r in results)


def test_retrieve_context_sorts_by_score_descending(monkeypatch):
    # Distances out of order on purpose: middle one is actually the most similar.
    fake_collection = _make_fake_collection(distances=[0.8, 0.1, 0.5])
    monkeypatch.setattr(retriever, "get_collection", lambda role: fake_collection)
    monkeypatch.setattr(
        retriever, "_get_embedding_model", lambda: MagicMock(encode=lambda texts: np.array([[0.1, 0.2, 0.3]]))
    )

    results = retriever.retrieve_context(role="ai_ml", skills=["PyTorch"], topics=[], min_score=0.0)

    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_context_respects_top_k(monkeypatch):
    fake_collection = _make_fake_collection(distances=[0.0, 0.1, 0.2, 0.3, 0.4])
    monkeypatch.setattr(retriever, "get_collection", lambda role: fake_collection)
    monkeypatch.setattr(
        retriever, "_get_embedding_model", lambda: MagicMock(encode=lambda texts: np.array([[0.1, 0.2, 0.3]]))
    )

    results = retriever.retrieve_context(role="ai_ml", skills=["PyTorch"], topics=[], top_k=2, min_score=0.0)

    assert len(results) == 2


def test_retrieve_context_returns_empty_for_empty_collection(monkeypatch):
    empty_collection = MagicMock()
    empty_collection.count.return_value = 0
    monkeypatch.setattr(retriever, "get_collection", lambda role: empty_collection)

    results = retriever.retrieve_context(role="ai_ml", skills=["PyTorch"], topics=[])

    assert results == []
    # Should short-circuit before ever touching the embedding model.
    empty_collection.query.assert_not_called()


def test_retrieve_for_question_generation_excludes_previous_topics(monkeypatch):
    fake_collection = _make_fake_collection(distances=[0.0])
    monkeypatch.setattr(retriever, "get_collection", lambda role: fake_collection)
    monkeypatch.setattr(
        retriever, "_get_embedding_model", lambda: MagicMock(encode=lambda texts: np.array([[0.1, 0.2, 0.3]]))
    )

    result = retriever.retrieve_for_question_generation(
        role="ai_ml",
        parsed_resume={
            "skills": ["PyTorch"],
            "technologies": ["Docker"],
            "domains": ["Neural Networks", "Overfitting"],
            "experience_level": "senior",
        },
        previous_topics=["Neural Networks"],
    )

    query_call = fake_collection.query.call_args
    assert result["experience_level"] == "senior"
    assert query_call is not None
