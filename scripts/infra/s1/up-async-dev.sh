#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKER_SERVICES=(celery-worker celery-beat)

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"

docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" up -d --build rabbitmq
COMPOSE_IGNORE_ORPHANS=true docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" up -d --build "${WORKER_SERVICES[@]}"

echo "S1 dev async services are up"
