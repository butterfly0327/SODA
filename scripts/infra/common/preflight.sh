#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REQUIRED_PATHS=(
  "$ROOT_DIR/frontend/docker-compose.yml"
  "$ROOT_DIR/frontend/docker-compose.dev.yml"
  "$ROOT_DIR/frontend/docker-compose.prod.yml"
  "$ROOT_DIR/backend/docker-compose.yml"
  "$ROOT_DIR/backend/docker-compose.dev.yml"
  "$ROOT_DIR/backend/docker-compose.prod.yml"
  "$ROOT_DIR/data-platform/docker-compose.yml"
  "$ROOT_DIR/data-platform/docker-compose.dev.yml"
  "$ROOT_DIR/data-platform/docker-compose.prod.yml"
  "$ROOT_DIR/data-platform/docker-compose.worker.yml"
  "$ROOT_DIR/data-platform/api"
  "$ROOT_DIR/data-platform/crawler/openapi"
  "$ROOT_DIR/data-platform/crawler/dataset"
  "$ROOT_DIR/infra/docker-compose.common.yml"
  "$ROOT_DIR/infra/docker-compose.local.yml"
  "$ROOT_DIR/infra/docker-compose.worker.yml"
  "$ROOT_DIR/infra/nginx/nginx.conf"
  "$ROOT_DIR/infra/nginx/upstream.conf"
  "$ROOT_DIR/.env.dev"
  "$ROOT_DIR/.env.prod"
)
REQUIRED_NETWORKS=(prod-net dev-net common-net monitoring-net ci-net)

for required_path in "${REQUIRED_PATHS[@]}"; do
  if [ ! -e "$required_path" ]; then
    echo "Missing required path: $required_path" >&2
    exit 1
  fi
done

docker compose --profile dev -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.dev.yml" config
docker compose --profile prod -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.prod.yml" config
docker compose --profile dev -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.dev.yml" config
docker compose --profile prod -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.prod.yml" config
docker compose --profile dev -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.dev.yml" config
docker compose --profile prod -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.prod.yml" config
docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" config
docker compose --env-file "$ROOT_DIR/.env.prod" --profile prod -f "$ROOT_DIR/infra/docker-compose.common.yml" config
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" -f "$ROOT_DIR/infra/docker-compose.local.yml" config

for network_name in "${REQUIRED_NETWORKS[@]}"; do
  docker network inspect "$network_name" >/dev/null
done

echo "Compose preflight checks passed"
