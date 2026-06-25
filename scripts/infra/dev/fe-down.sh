#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

docker compose --profile dev -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.dev.yml" down

echo "Frontend dev service is down"
