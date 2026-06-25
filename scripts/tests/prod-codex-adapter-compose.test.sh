#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CFG="$(docker compose \
  --env-file "$ROOT_DIR/.env.prod" \
  --profile prod \
  -f "$ROOT_DIR/data-platform/docker-compose.yml" \
  -f "$ROOT_DIR/data-platform/docker-compose.prod.yml" \
  config)"

printf '%s\n' "$CFG" | rg -q '^  codex-adapter-prod:$'
printf '%s\n' "$CFG" | rg -q 'image: soda-codex-adapter:prod'
printf '%s\n' "$CFG" | rg -q 'dockerfile: data-platform/codex_adapter/Dockerfile.prod'
printf '%s\n' "$CFG" | rg -F -q 'CODEX_MODEL: gpt-5.4'
printf '%s\n' "$CFG" | rg -F -q 'CODEX_HOME_PATH: /root/.codex'
printf '%s\n' "$CFG" | rg -F -q 'source: /home/ubuntu/codex-home-prod'
printf '%s\n' "$CFG" | rg -F -q 'target: /root/.codex'
printf '%s\n' "$CFG" | rg -F -q 'CODEX_ADAPTER_BASE_URL: http://codex-adapter-prod:8091'

rg -q 'codex-adapter-prod' "$ROOT_DIR/scripts/infra/s1/ps-prod.sh"

echo "prod-codex-adapter-compose tests passed"
