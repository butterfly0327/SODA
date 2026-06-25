#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/scripts/infra/s1/up-async-dev.sh"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "missing script: $SCRIPT_PATH" >&2
  exit 1
fi

grep -F 'bootstrap-networks.sh' "$SCRIPT_PATH" >/dev/null
grep -F 'docker compose -f "$ROOT_DIR/infra/docker-compose.worker.yml" up -d --build rabbitmq' "$SCRIPT_PATH" >/dev/null
grep -F 'docker compose -f "$ROOT_DIR/data-platform/docker-compose.worker.yml" up -d --build "${WORKER_SERVICES[@]}"' "$SCRIPT_PATH" >/dev/null

echo "PASS: dev async startup script wires expected compose commands"
