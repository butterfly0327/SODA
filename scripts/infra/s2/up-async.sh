#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKER_SERVICES=(celery-worker-prod celery-beat-prod)

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"

docker compose -f "$ROOT_DIR/infra/docker-compose.worker.prod.yml" up -d --build rabbitmq-prod
COMPOSE_IGNORE_ORPHANS=true docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.prod.yml" up -d --build "${WORKER_SERVICES[@]}"

echo "S2 prod async services are up"
