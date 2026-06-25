#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/scripts/infra/s1/down-async-dev.sh"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "missing script: $SCRIPT_PATH" >&2
  exit 1
fi

grep -F 'docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" down' "$SCRIPT_PATH" >/dev/null
grep -F 'docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" stop rabbitmq' "$SCRIPT_PATH" >/dev/null
grep -F 'docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" rm -f rabbitmq' "$SCRIPT_PATH" >/dev/null
if grep -F 'docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" down' "$SCRIPT_PATH" >/dev/null; then
  echo "dev async shutdown must not bring down the entire infra worker compose stack" >&2
  exit 1
fi

echo "PASS: dev async shutdown targets rabbitmq only"
