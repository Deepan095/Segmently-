#!/usr/bin/env bash
# Segmently production helper. Run from the repo root on the VPS.
#   ./deploy/segmently.sh up | update | migrate | seed | logs | ps | backup | down
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE=(docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod)

case "${1:-}" in
  up)
    "${COMPOSE[@]}" up -d --build
    "$0" migrate
    "$0" seed
    "${COMPOSE[@]}" ps
    ;;
  update)
    git pull
    "${COMPOSE[@]}" up -d --build
    "$0" migrate
    "${COMPOSE[@]}" ps
    ;;
  migrate)
    "${COMPOSE[@]}" exec -T api alembic upgrade head
    ;;
  seed)
    "${COMPOSE[@]}" exec -T api python -m scripts.seed
    ;;
  logs)
    shift || true
    "${COMPOSE[@]}" logs -f --tail=100 "$@"
    ;;
  ps)
    "${COMPOSE[@]}" ps
    ;;
  backup)
    ts=$(date +%Y%m%d-%H%M%S)
    mkdir -p backups
    "${COMPOSE[@]}" exec -T db pg_dump -U "${POSTGRES_USER:-segmently}" \
      "${POSTGRES_DB:-segmently}" | gzip > "backups/db-${ts}.sql.gz"
    echo "wrote backups/db-${ts}.sql.gz"
    ;;
  down)
    "${COMPOSE[@]}" down
    ;;
  *)
    echo "usage: $0 {up|update|migrate|seed|logs [svc]|ps|backup|down}" >&2
    exit 1
    ;;
esac
