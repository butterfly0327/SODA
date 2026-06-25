#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

docker compose --profile dev -f "$ROOT_DIR/backend/docker-compose.yml" -f "$ROOT_DIR/backend/docker-compose.dev.yml" logs -f --tail 100 dev-spring
