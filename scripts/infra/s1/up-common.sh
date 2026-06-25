#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.prod"

docker compose --env-file "$ENV_FILE" --profile prod -f "$ROOT_DIR/infra/docker-compose.common.yml" up -d \
  nginx \
  promtail-s1 \
  cadvisor-s1 \
  node-exporter-s1 \
  nginx-prometheus-exporter

echo "S1 common services are up"
