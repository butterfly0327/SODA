#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

COMPOSE_IGNORE_ORPHANS=true docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" down
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" stop rabbitmq || true
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" rm -f rabbitmq || true

echo "S1 dev async services are down"
