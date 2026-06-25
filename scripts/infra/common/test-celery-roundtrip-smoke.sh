#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/scripts/infra/common/celery-roundtrip-smoke.sh"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "missing script: $SCRIPT_PATH" >&2
  exit 1
fi

grep -F 'exec -T' "$SCRIPT_PATH" >/dev/null
if grep -F 'run --rm --no-deps' "$SCRIPT_PATH" >/dev/null; then
  echo "roundtrip smoke must exec into the running worker, not run a fresh container" >&2
  exit 1
fi

echo "PASS: celery roundtrip smoke uses running worker container"
