FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bakes the embedding model weights into the image so no host without a persistent
# disk (e.g. a free-tier platform) has to download them from the network on every
# cold start - it's just there already.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

RUN mkdir -p data/chroma knowledge_base/ai_ml knowledge_base/data_science

# ingest.py is idempotent (skips a role's collection if already populated), so it's
# safe to run on every container start rather than requiring a manual one-time step
# that's easy to forget on a fresh deployment (empty ChromaDB = ungrounded questions,
# with no error surfaced).
CMD ["sh", "-c", "alembic upgrade head && python ingest.py --role all && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
