#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.worker.prod.yml"
ALERTMANAGER_CONFIG="$ROOT_DIR/infra/monitoring/alertmanager.yml"

test -f "$COMPOSE_FILE"
test -f "$ALERTMANAGER_CONFIG"

! rg -Fq -- '--config.expand-env' "$COMPOSE_FILE"
rg -Fq 'entrypoint: ["/bin/sh", "-ec"]' "$COMPOSE_FILE"
rg -Fq 'sed \' "$COMPOSE_FILE"
rg -Fq '__MATTERMOST_WEBHOOK_URL__' "$ALERTMANAGER_CONFIG"
! rg -Fq '${MATTERMOST_WEBHOOK_URL}' "$ALERTMANAGER_CONFIG"

echo "prod-alertmanager-config tests passed"
