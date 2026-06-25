#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

docker compose --profile prod -f "$ROOT_DIR/infra/docker-compose.common.yml" stop \
  nginx \
  promtail-s1 \
  cadvisor-s1 \
  node-exporter-s1 \
  nginx-prometheus-exporter
docker compose --profile prod -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.prod.yml" down
docker compose --profile prod -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.prod.yml" down
docker compose --profile prod -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.prod.yml" down

echo "S1 prod stack is down"
