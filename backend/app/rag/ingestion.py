"""
RAG Knowledge Ingestion Pipeline

Loads role-specific PDFs → chunks text (512 tokens, 64 overlap) →
generates sentence-transformer embeddings → stores in ChromaDB.

Design choices:
- Recursive character splitting preserves sentence/paragraph context better than
  fixed-size splits, reducing mid-sentence chunk boundaries.
- 64-token overlap ensures concepts spanning chunk boundaries are retrievable.
- Metadata (role, source, chapter, page) enables role-filtered retrieval.
"""

import contextlib
import logging
import os
from functools import lru_cache
from pathlib import Path

import chromadb
import fitz  # PyMuPDF
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

ROLE_COLLECTION_MAP = {
    "ai_ml": "knowledge_ai_ml",
    "data_science": "knowledge_data_science",
}


@lru_cache(maxsize=1)
def _get_chroma_client() -> chromadb.PersistentClient:
    """Cached: a fresh PersistentClient re-opens the sqlite connection every call."""
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    return chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


@lru_cache(maxsize=1)
def _get_embedding_model() -> SentenceTransformer:
    """
    Cached: without this, every single call re-loads ~90MB of model weights from
    disk — this was happening on every question generated during an interview,
    not just once at startup.
    """
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def _extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """Returns list of {text, page, source} dicts."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            pages.append(
                {
                    "text": text,
                    "page": page_num,
                    "source": Path(pdf_path).name,
                }
            )
    doc.close()
    return pages


def _recursive_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Splits text recursively: paragraph → sentence → word level.
    Ensures chunks stay near chunk_size characters while respecting boundaries.
    """
    separators = ["\n\n", "\n", ". ", " ", ""]

    def split_with_sep(text: str, sep: str) -> list[str]:
        if not sep:
            return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
        parts = text.split(sep)
        chunks, current = [], ""
        for part in parts:
            candidate = current + sep + part if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                current = part
        if current:
            chunks.append(current.strip())
        return chunks

    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    for sep in separators:
        splits = split_with_sep(text, sep)
        if all(len(s) <= chunk_size * 1.2 for s in splits):
            if not sep:
                # The character-slice fallback already builds overlap in via its
                # stride (chunk_size - overlap); prepending another tail below would
                # double-apply it and inflate chunks past chunk_size.
                return [s.strip() for s in splits if s.strip()]

            # Add overlap between consecutive chunks
            result = []
            for i, chunk in enumerate(splits):
                if i > 0 and len(splits[i - 1]) > overlap:
                    tail = splits[i - 1][-overlap:]
                    chunk = tail + " " + chunk
                result.append(chunk.strip())
            return [c for c in result if c]

    return split_with_sep(text, "")


def ingest_role_documents(role: str, force_reingest: bool = False) -> int:
    """
    Ingests all PDFs in knowledge_base/{role}/ into ChromaDB.
    Returns number of chunks stored.
    """
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR) / role
    if not kb_dir.exists():
        logger.warning(f"Knowledge base directory not found: {kb_dir}")
        return 0

    pdf_files = list(kb_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {kb_dir}")
        return 0

    client = _get_chroma_client()
    collection_name = ROLE_COLLECTION_MAP.get(role, f"knowledge_{role}")

    if force_reingest:
        with contextlib.suppress(Exception):
            client.delete_collection(collection_name)

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Skip if already ingested and not forcing
    if not force_reingest and collection.count() > 0:
        logger.info(f"Collection '{collection_name}' already has {collection.count()} chunks. Skipping.")
        return collection.count()

    model = _get_embedding_model()
    total_chunks = 0

    for pdf_path in pdf_files:
        logger.info(f"Processing: {pdf_path.name}")
        pages = _extract_text_from_pdf(str(pdf_path))

        for page_data in pages:
            chunks = _recursive_split(
                page_data["text"],
                settings.CHUNK_SIZE,
                settings.CHUNK_OVERLAP,
            )

            if not chunks:
                continue

            embeddings = model.encode(chunks, show_progress_bar=False).tolist()

            ids = [f"{role}_{pdf_path.stem}_p{page_data['page']}_c{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "role": role,
                    "source": page_data["source"],
                    "page": page_data["page"],
                    "chunk_index": i,
                }
                for i in range(len(chunks))
            ]

            # ChromaDB upsert in batches of 100
            batch_size = 100
            for start in range(0, len(chunks), batch_size):
                end = start + batch_size
                collection.upsert(
                    ids=ids[start:end],
                    documents=chunks[start:end],
                    embeddings=embeddings[start:end],
                    metadatas=metadatas[start:end],
                )

            total_chunks += len(chunks)
            logger.info(f"  Page {page_data['page']}: {len(chunks)} chunks")

    logger.info(f"Ingestion complete. Total chunks stored: {total_chunks}")
    return total_chunks


def run_startup_ingest_if_empty() -> None:
    """
    Ingest every role's knowledge base if ChromaDB is empty or missing.

    Meant to be run from a background thread kicked off in the app's lifespan
    (see app/main.py), not from the container's CMD. Shelling this out with a
    POSIX `&` before starting uvicorn was tried first and was unreliable — dash's
    subshell/backgrounding semantics don't reliably detach the job, so the
    platform's port scan kept timing out waiting for uvicorn to bind. Running it
    as a real background thread inside the same process guarantees uvicorn binds
    the port immediately regardless of how long ingestion takes (large PDFs on a
    free-tier CPU can take 10+ minutes); RAG questions just fall back to a
    generic question until ingestion finishes.
    """
    persist_dir = settings.CHROMA_PERSIST_DIR
    if os.path.isdir(persist_dir) and any(True for _ in os.scandir(persist_dir)):
        logger.info("ChromaDB already populated at %s, skipping startup ingest.", persist_dir)
        return

    logger.info("ChromaDB empty — running startup ingest in the background...")
    for role in ROLE_COLLECTION_MAP:
        try:
            ingest_role_documents(role)
        except Exception:
            logger.exception("Startup ingest failed for role %r", role)


def get_collection(role: str) -> chromadb.Collection:
    client = _get_chroma_client()
    collection_name = ROLE_COLLECTION_MAP.get(role, f"knowledge_{role}")
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
