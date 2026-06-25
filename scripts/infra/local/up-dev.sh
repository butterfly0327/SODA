#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WORKER_SERVICES=(celery-worker celery-beat)
SKIP_DEV_BUILD="${SODA_SKIP_DEV_BUILD:-0}"

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"
if [[ "$SKIP_DEV_BUILD" != "1" ]]; then
  bash "$ROOT_DIR/scripts/infra/common/build-backend-dev.sh"
fi

docker compose -f "$ROOT_DIR/frontend/docker-compose.yml" up -d prod-frontend
docker compose -f "$ROOT_DIR/backend/docker-compose.yml" up -d spring-blue
docker compose -f "$ROOT_DIR/data-platform/docker-compose.yml" up -d fastapi-prod
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" -f "$ROOT_DIR/infra/docker-compose.local.yml" up -d rabbitmq jenkins grafana loki prometheus

docker compose --profile dev -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.dev.yml" up -d
docker compose --profile dev -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.dev.yml" up -d
docker compose --profile dev -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.dev.yml" up -d
docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" up -d "${WORKER_SERVICES[@]}"
docker compose -f "$ROOT_DIR/infra/docker-compose.common.yml" up -d nginx

echo "Local integrated dev stack startup commands completed"
