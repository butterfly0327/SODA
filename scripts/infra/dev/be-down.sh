#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

COMPOSE_IGNORE_ORPHANS=true docker compose --profile dev -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.dev.yml" down
COMPOSE_IGNORE_ORPHANS=true docker compose --profile dev -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.dev.yml" stop dev-postgres dev-redis minio
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" stop rabbitmq

echo "Backend dev service and dependencies are down"
