#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKER_SERVICES=(celery-worker celery-beat)

docker compose -f "$ROOT_DIR/infra/docker-compose.common.yml" down
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" -f "$ROOT_DIR/infra/docker-compose.local.yml" down
COMPOSE_IGNORE_ORPHANS=true docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" rm -fsv "${WORKER_SERVICES[@]}" || true
docker compose --profile dev -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.dev.yml" down
docker compose --profile dev -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.dev.yml" down
docker compose --profile dev -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.dev.yml" down
docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" down
docker compose -f "$ROOT_DIR/data-platform/docker-compose.yml" down
docker compose -f "$ROOT_DIR/backend/docker-compose.yml" down
docker compose -f "$ROOT_DIR/frontend/docker-compose.yml" down

echo "Local integrated dev stack is down"
