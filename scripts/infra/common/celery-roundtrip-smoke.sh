#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <env-file> <compose-file> [service] [timeout-seconds]" >&2
  exit 1
}

ENV_FILE="${1:-}"
COMPOSE_FILE="${2:-}"
SERVICE_NAME="${3:-celery-worker-prod}"
TIMEOUT_SECONDS="${4:-30}"

if [[ -z "$ENV_FILE" || -z "$COMPOSE_FILE" ]]; then
  usage
fi

COMPOSE_IGNORE_ORPHANS=true docker compose \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_FILE" \
  exec -T \
  -e CELERY_SMOKE_TIMEOUT="$TIMEOUT_SECONDS" \
  "$SERVICE_NAME" \
  python -c "import os; from app.tasks.platform_tasks import ping; result = ping.delay(); payload = result.get(timeout=int(os.environ.get('CELERY_SMOKE_TIMEOUT', '30'))); assert isinstance(payload, dict) and payload.get('status') == 'ok' and payload.get('service') == 'celery', payload; print(payload)"
