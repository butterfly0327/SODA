#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

docker compose \
  --env-file "$ROOT_DIR/.env.prod" \
  -f "$ROOT_DIR/infra/docker-compose.worker.prod.yml" \
  config --format json > "$TMP_JSON"

python3 - "$TMP_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    cfg = json.load(fh)

svc = cfg["services"]["prometheus-prod"]
command = svc.get("command")
entrypoint = svc.get("entrypoint")

assert entrypoint == ["/bin/sh", "-ec"], entrypoint
assert isinstance(command, list), type(command).__name__
assert len(command) == 1, command
script = command[0]
assert "sed \\" in script, script
assert "exec /bin/prometheus" in script, script
assert "__PROD_RDS_HOST__" in script, script
PY

echo "prometheus-monitoring-command tests passed"
