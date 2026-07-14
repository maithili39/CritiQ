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
#   2. Start uvicorn immediately so the platform's port scan succeeds right away.
#   3. Kick off ingest.py in the background, only if ChromaDB is empty or missing,
#      so redeploying onto a persistent disk doesn't re-ingest from scratch every
#      time. Ingestion runs one page's chunks through the embedding model per
#      call, which on a free-tier CPU can take 10+ minutes for a large PDF —
#      running it *before* uvicorn bound the port made every deploy without a
#      persistent disk time out on the platform's port scan (RAG questions will
#      fall back to a generic question until ingestion finishes in the background;
#      that's a much better failure mode than the whole deploy dying).
CMD ["sh", "-c", "\
  alembic upgrade head && \
  ( python -c \"\
import os, sys\n\
d = os.environ.get('CHROMA_PERSIST_DIR', 'data/chroma')\n\
populated = os.path.isdir(d) and any(True for _ in os.scandir(d))\n\
sys.exit(0 if populated else 1)\
\" && echo 'ChromaDB already populated, skipping ingest.' \
  || (echo 'ChromaDB empty — running ingest in the background...' && python ingest.py --role all) & ) && \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
