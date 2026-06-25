#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.dev"
SKIP_DEV_BUILD="${SODA_SKIP_DEV_BUILD:-0}"

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"
if [[ "$SKIP_DEV_BUILD" != "1" ]]; then
  bash "$ROOT_DIR/scripts/infra/common/build-backend-dev.sh"
fi

compose_up() {
  local label="$1"
  shift
  local attempt

  for attempt in 1 2; do
    if docker compose --env-file "$ENV_FILE" --profile dev "$@" up -d; then
      return 0
    fi

    if [[ "$attempt" -eq 2 ]]; then
      echo "Failed to start $label after retry" >&2
      return 1
    fi

    echo "Retrying $label startup after transient docker compose failure..." >&2
    sleep 3
  done
}

compose_up_force_recreate_service() {
  local label="$1"
  local service_name="$2"
  shift 2
  local attempt

  for attempt in 1 2; do
    if docker compose --env-file "$ENV_FILE" --profile dev "$@" up -d --force-recreate "$service_name"; then
      return 0
    fi

    if [[ "$attempt" -eq 2 ]]; then
      echo "Failed to recreate $label after retry" >&2
      return 1
    fi

    echo "Retrying $label recreation after transient docker compose failure..." >&2
    sleep 3
  done
}

compose_up_force_recreate_service "frontend dev stack" dev-frontend -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.dev.yml"
compose_up_force_recreate_service "backend dev app" dev-spring -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.dev.yml"
compose_up "data-platform dev stack" -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.dev.yml"
compose_up_force_recreate_service "data-platform dev app" fastapi-dev -f "$ROOT_DIR/data-platform/docker-compose.yml" -f "$ROOT_DIR/data-platform/docker-compose.dev.yml"

echo "S1 dev stack startup commands completed"
