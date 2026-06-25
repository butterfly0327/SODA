#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"
docker compose --profile dev -f "$ROOT_DIR/frontend/docker-compose.yml" -f "$ROOT_DIR/frontend/docker-compose.dev.yml" up -d

echo "Frontend dev service is up"
