#!/usr/bin/env bash
# Backs up the Postgres database (pg_dump, custom format) and the ChromaDB
# persistence directory (tarball) into backend/backups/<timestamp>/.
#
# Usage: ./scripts/backup.sh
# Requires: pg_dump on PATH (matching the target Postgres major version),
#           DATABASE_URL set (loaded from .env if present).
set -euo pipefail

cd "$(dirname "$0")/.."   # -> backend/

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

: "${DATABASE_URL:?DATABASE_URL is not set (check .env)}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="backups/${TIMESTAMP}"
mkdir -p "${OUT_DIR}"

echo "==> Dumping Postgres database..."
pg_dump --dbname="${DATABASE_URL}" --format=custom --file="${OUT_DIR}/screening.dump"

echo "==> Archiving ChromaDB persistence dir..."
if [ -d "data/chroma" ]; then
  tar -czf "${OUT_DIR}/chroma.tar.gz" -C data chroma
else
  echo "    (data/chroma not found, skipping)"
fi

echo "==> Backup complete: ${OUT_DIR}"
du -sh "${OUT_DIR}"/* 2>/dev/null || true
