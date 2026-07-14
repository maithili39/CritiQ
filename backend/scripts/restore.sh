#!/usr/bin/env bash
# Restores a backup produced by backup.sh.
#
# Usage: ./scripts/restore.sh backups/20260702_140000
# WARNING: this drops and recreates every table in the target database.
#
# Set RESTORE_CONFIRM=yes to skip the interactive prompt (used by the automated
# backup/restore drill in CI — see .github/workflows/ci.yml — where there's no
# terminal to answer a `read -p`).
set -euo pipefail

cd "$(dirname "$0")/.."   # -> backend/

BACKUP_DIR="${1:?Usage: restore.sh <backup_dir>}"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

: "${DATABASE_URL:?DATABASE_URL is not set (check .env)}"

if [ ! -f "${BACKUP_DIR}/screening.dump" ]; then
  echo "No screening.dump found in ${BACKUP_DIR}" >&2
  exit 1
fi

if [ "${RESTORE_CONFIRM:-}" != "yes" ]; then
  read -p "This will DROP and restore the database at ${DATABASE_URL}. Continue? [y/N] " confirm
  [ "${confirm}" = "y" ] || { echo "Aborted."; exit 1; }
fi

echo "==> Restoring Postgres database..."
PG_URL="${DATABASE_URL/postgresql+psycopg:/postgresql:}"
pg_restore --dbname="${PG_URL}" --clean --if-exists --no-owner "${BACKUP_DIR}/screening.dump"

if [ -f "${BACKUP_DIR}/chroma.tar.gz" ]; then
  echo "==> Restoring ChromaDB persistence dir..."
  rm -rf data/chroma
  tar -xzf "${BACKUP_DIR}/chroma.tar.gz" -C data
fi

echo "==> Restore complete."
