#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKER_SERVICES=(celery-worker-prod celery-beat-prod)

docker compose -f "$ROOT_DIR/infra/docker-compose.worker.prod.yml" stop rabbitmq-prod || true
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.prod.yml" rm -fsv rabbitmq-prod || true
COMPOSE_IGNORE_ORPHANS=true docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.prod.yml" stop "${WORKER_SERVICES[@]}" || true
COMPOSE_IGNORE_ORPHANS=true docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.prod.yml" rm -fsv "${WORKER_SERVICES[@]}" || true

echo "S2 prod async services are down"
