#!/usr/bin/env bash
# One-command bring-up of CineForge AI on a Docker host (VPS / single-box).
#
# Usage (on the host):
#   bash infra/deploy.sh
# Required environment (or existing .env in the repo root):
#   JWT_SECRET (>=64 random chars), DOMAIN or PUBLIC_API_URL (optional, CORS)
# Optional provider keys: REPLICATE_API_TOKEN, FAL_KEY, STRIPE_* , S3_*
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

if [[ ! -f .env ]]; then
  echo "no .env found — creating one from .env.example (fill it, then re-run)"
  cp .env.example .env
  echo "Wrote .env. Edit it (at minimum JWT_SECRET), then re-run: bash infra/deploy.sh"
  exit 1
fi

echo "==> building + starting services"
docker compose -f infra/docker/docker-compose.yml up -d --build

echo "==> waiting for API /health"
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "API healthy"
    break
  fi
  sleep 2
done
curl -sf http://127.0.0.1:8000/health >/dev/null || { echo "API did not become healthy — check: docker compose logs api"; exit 1; }

echo "==> worker alive? (worker_loop prints to data/worker.log)"
docker compose -f infra/docker/docker-compose.yml ps worker

echo "==> done. Web UI on port 3000, API on 8000."
echo "    register the first account with an email in ADMIN_EMAILS to get admin."
