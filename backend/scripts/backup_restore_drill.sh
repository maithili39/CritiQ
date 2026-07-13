#!/usr/bin/env bash
# Proves backup.sh/restore.sh actually round-trip data, instead of just existing
# untested. Run against a scratch database — this seeds a marker row, backs it up,
# destroys the database, restores from the backup, and verifies the marker survived.
#
# Usage: DATABASE_URL=postgresql+psycopg://... ./scripts/backup_restore_drill.sh
# Wired into CI (.github/workflows/ci.yml) against a throwaway Postgres service
# container — never run this against a database you care about.
set -euo pipefail

cd "$(dirname "$0")/.."   # -> backend/

: "${DATABASE_URL:?DATABASE_URL is not set}"

# psycopg-style URL (postgresql+psycopg://...) -> plain libpq URL for psql/pg_dump.
PG_URL="${DATABASE_URL/postgresql+psycopg:/postgresql:}"

MARKER_EMAIL="backup-drill-marker@example.com"

echo "==> Applying migrations to scratch database..."
alembic upgrade head

echo "==> Seeding a marker row..."
psql "${PG_URL}" -c \
  "INSERT INTO users (id, email, password_hash, is_admin, email_verified, failed_login_attempts) \
   VALUES (gen_random_uuid()::text, '${MARKER_EMAIL}', 'x', false, false, 0);"

echo "==> Running backup.sh..."
DATABASE_URL="${DATABASE_URL}" ./scripts/backup.sh
LATEST_BACKUP=$(ls -td backups/*/ | head -1)
echo "    using backup: ${LATEST_BACKUP}"

echo "==> Destroying the database to prove restore isn't a no-op..."
psql "${PG_URL}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "==> Confirming the marker is really gone..."
if psql "${PG_URL}" -tAc "SELECT 1 FROM users WHERE email = '${MARKER_EMAIL}'" 2>/dev/null | grep -q 1; then
  echo "Marker row survived the drop — drill is not testing anything real." >&2
  exit 1
fi

echo "==> Restoring from backup..."
RESTORE_CONFIRM=yes DATABASE_URL="${DATABASE_URL}" ./scripts/restore.sh "${LATEST_BACKUP}"

echo "==> Verifying the marker row came back..."
if ! psql "${PG_URL}" -tAc "SELECT 1 FROM users WHERE email = '${MARKER_EMAIL}'" | grep -q 1; then
  echo "Marker row did NOT come back — the backup is not actually restorable." >&2
  exit 1
fi

echo "==> Backup/restore drill passed: data survived a real dump -> destroy -> restore cycle."
