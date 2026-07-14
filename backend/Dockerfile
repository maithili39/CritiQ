# Keep in sync with the python-version in .github/workflows/ci.yml — tests run on the
# same Python version as the deployed artifact so version-specific behaviour is caught by CI.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# Install the CPU-only PyTorch wheel first so sentence-transformers' dependency
# resolution picks it up instead of pulling the full CUDA/GPU build (multiple
# GB of nvidia_* packages this CPU-only container never uses).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Bakes the embedding model weights into the image so no host without a persistent
# disk (e.g. a free-tier platform) has to download them from the network on every
# cold start - it's just there already.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

RUN mkdir -p data/chroma knowledge_base/ai_ml knowledge_base/data_science

# Start-up sequence:
#   1. Run Alembic migrations (safe to re-run — idempotent).
#   2. Start uvicorn, which binds the port immediately.
# Knowledge-base ingestion (if ChromaDB is empty or missing) runs from the app's
# own lifespan (see app/main.py + app/rag/ingestion.py:run_startup_ingest_if_empty)
# as a background thread, not from this shell script — a `python ingest.py & `
# backgrounding trick here was tried first and didn't reliably detach on this
# image's `sh` (dash), leaving uvicorn's port bind blocked behind however long
# ingestion took (10+ minutes for a large PDF on a free-tier CPU), which is
# exactly what caused the platform's port scan to keep timing out.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
