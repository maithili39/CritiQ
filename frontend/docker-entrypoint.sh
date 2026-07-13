#!/bin/sh
# Writes window.__API_BASE__ from the API_BASE env var at container start (not at
# `docker build` time) so the same built image works across environments — change
# API_BASE and restart the container, no rebuild needed.
set -e

API_BASE="${API_BASE:-/api}"
cat > /app/dist/config.js <<EOF
window.__API_BASE__ = "${API_BASE}";
EOF

exec "$@"
