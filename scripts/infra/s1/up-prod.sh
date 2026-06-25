#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.prod"

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"

docker compose --env-file "$ENV_FILE" --profile prod -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.prod.yml" up -d --build

sudo rm -rf "$ROOT_DIR/backend/build" "$ROOT_DIR/backend/.gradle"
sudo install -d -m 775 "$ROOT_DIR/backend/build" "$ROOT_DIR/backend/.gradle"

sudo docker run --rm \
  -u 0:0 \
  -e GRADLE_USER_HOME=/tmp/.gradle \
  -v "$ROOT_DIR/backend:/workspace" \
  -w /workspace \
  gradle:8.14.4-jdk21-alpine \
  sh -lc 'chmod +x gradlew && ./gradlew clean bootJar -x test --no-daemon'

docker compose --env-file "$ENV_FILE" --profile prod -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.prod.yml" up -d --build
docker compose --env-file "$ENV_FILE" --profile prod -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.prod.yml" up -d --build
docker compose --env-file "$ENV_FILE" --profile prod -f "$ROOT_DIR/infra/docker-compose.common.yml" up -d \
  nginx \
  promtail-s1 \
  cadvisor-s1 \
  node-exporter-s1 \
  nginx-prometheus-exporter

echo "S1 prod stack startup commands completed"
