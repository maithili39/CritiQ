"""
RAG Retrieval Service

Constructs dynamic queries from resume + role, retrieves top-k chunks
from ChromaDB using cosine similarity, and filters by relevance threshold.
"""



from app.core.config import settings
from app.rag.ingestion import _get_embedding_model, get_collection


def _build_query(role: str, skills: list[str], topics: list[str], focus: str = "") -> str:
    """
    Builds a retrieval query combining role context, candidate skills, and focus area.
    Richer queries yield more relevant chunks than simple keyword lookup.
    """
    role_label = role.replace("_", " ").title()
    skill_str = ", ".join(skills[:8]) if skills else "general concepts"
    topic_str = ", ".join(topics[:4]) if topics else ""

    query = f"{role_label} interview: {skill_str}"
    if topic_str:
        query += f". Topics: {topic_str}"
    if focus:
        query += f". Focus: {focus}"
    return query


def retrieve_context(
    role: str,
    skills: list[str],
    topics: list[str],
    focus: str = "",
    top_k: int | None = None,
    min_score: float = 0.25,
) -> list[dict]:
    """
    Retrieves relevant knowledge chunks for question generation.

    Returns list of {text, source, page, score} dicts, sorted by relevance.
    Filters out chunks below min_score to avoid noisy context.
    """
    top_k = top_k or settings.TOP_K_RETRIEVAL
    collection = get_collection(role)

    if collection.count() == 0:
        return []

    model = _get_embedding_model()
    query = _build_query(role, skills, topics, focus)
    query_embedding = model.encode([query])[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k * 2, collection.count()),  # over-fetch, then filter
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0], strict=False,
    ):
        # ChromaDB cosine distance: 0=identical, 2=opposite. Convert to similarity.
        similarity = 1 - (dist / 2)
        if similarity >= min_score:
            chunks.append({
                "text": doc,
                "source": meta.get("source", ""),
                "page": meta.get("page", 0),
                "score": round(similarity, 4),
            })

    # Sort by score descending, return top_k
    chunks.sort(key=lambda x: x["score"], reverse=True)
    return chunks[:top_k]


def retrieve_for_question_generation(
    role: str,
    parsed_resume: dict,
    previous_topics: list[str] | None = None,
    focus_topic: str = "",
) -> dict:
    """
    High-level retrieval call used by the question generator.

    Avoids re-using topics already covered in the interview by
    steering the query away from previous_topics.
    """
    skills = parsed_resume.get("skills", [])
    technologies = parsed_resume.get("technologies", [])
    experience_level = parsed_resume.get("experience_level", "mid")
    all_skills = skills + technologies

    # Build topic list from resume, excluding already-covered topics
    candidate_topics = parsed_resume.get("domains", [])
    if previous_topics:
        candidate_topics = [t for t in candidate_topics if t not in previous_topics]

    chunks = retrieve_context(
        role=role,
        skills=all_skills,
        topics=candidate_topics,
        focus=focus_topic,
        top_k=settings.TOP_K_RETRIEVAL,
    )

    return {
        "chunks": chunks,
        "query_skills": all_skills[:8],
        "experience_level": experience_level,
        "context_text": "\n\n---\n\n".join(c["text"] for c in chunks),
        "sources": [{"source": c["source"], "page": c["page"]} for c in chunks],
    }
