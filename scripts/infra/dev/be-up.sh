#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SKIP_DEV_BUILD="${SODA_SKIP_DEV_BUILD:-0}"

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"
if [[ "$SKIP_DEV_BUILD" != "1" ]]; then
  bash "$ROOT_DIR/scripts/infra/common/build-backend-dev.sh"
fi
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" up -d rabbitmq
COMPOSE_IGNORE_ORPHANS=true docker compose --profile dev -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.dev.yml" up -d dev-postgres dev-redis minio
COMPOSE_IGNORE_ORPHANS=true docker compose --profile dev -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.dev.yml" up -d

for attempt in $(seq 1 90); do
  if curl -fsS http://localhost:18085/health >/dev/null 2>&1; then
    echo "Backend dev service and dependencies are up"
    exit 0
  fi
  sleep 2
done

echo "Backend dev service did not become ready within timeout" >&2
exit 1
