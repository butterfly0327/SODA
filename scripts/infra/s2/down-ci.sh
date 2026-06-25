#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

docker compose -f "$ROOT_DIR/infra/docker-compose.worker.prod.yml" stop jenkins-prod

echo "S2 prod CI stack stopped"
