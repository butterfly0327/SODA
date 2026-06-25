#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKER_SERVICES=(celery-worker celery-beat)

docker compose -f "$ROOT_DIR/infra/docker-compose.common.yml" ps
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" -f "$ROOT_DIR/infra/docker-compose.local.yml" ps
docker compose --profile dev -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.dev.yml" ps
docker compose --profile dev -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.dev.yml" ps
docker compose --profile dev -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.dev.yml" ps
docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" ps "${WORKER_SERVICES[@]}"

echo "Local integrated dev stack status listed"
