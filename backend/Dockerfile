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
#   2. Run ingest.py only if ChromaDB is empty or missing, so redeploying onto a
#      persistent disk doesn't re-ingest 3 PDFs from scratch every time (~30-60 s).
#      The python one-liner exits with code 0 ("already populated, skip") or 1
#      ("empty/missing, proceed"). On local dev / free-tier without a persistent disk
#      the dir is always empty at start, so the full ingest still runs.
#   3. Start uvicorn.
CMD ["sh", "-c", "\
  alembic upgrade head && \
  python -c \"\
import os, sys\n\
d = os.environ.get('CHROMA_PERSIST_DIR', 'data/chroma')\n\
populated = os.path.isdir(d) and any(True for _ in os.scandir(d))\n\
sys.exit(0 if populated else 1)\
\" && echo 'ChromaDB already populated, skipping ingest.' \
  || (echo 'ChromaDB empty — running ingest...' && python ingest.py --role all) && \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
