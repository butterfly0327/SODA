#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/scripts/infra/dev/be-dev-run.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ENV_FILE="$TMP_DIR/.env.dev"
KEY_FILE="$TMP_DIR/dev.pem"
OUT_FILE="$TMP_DIR/out.log"

cat >"$ENV_FILE" <<'EOF'
DEV_POSTGRES_DB=soda_dev
DEV_POSTGRES_USER=soda
DEV_POSTGRES_PASSWORD=change-me
DEV_REDIS_HOST=dev-redis
DEV_REDIS_PORT=6379
EOF

touch "$KEY_FILE"

export SODA_DEV_ENV_FILE="$ENV_FILE"
export SODA_DEV_SSH_KEY_PATH="$KEY_FILE"
export SODA_DEV_RUN_DRY_RUN=1
export SODA_DEV_LOCAL_DB_PORT=25432
export SODA_DEV_LOCAL_REDIS_PORT=26379
export SODA_DEV_REMOTE_DB_PORT=15432
export SODA_DEV_REMOTE_REDIS_PORT=16379

if ! bash "$SCRIPT_PATH" >"$OUT_FILE" 2>&1; then
  echo "[FAIL] be-dev-run dry-run exited non-zero" >&2
  cat "$OUT_FILE" >&2
  exit 1
fi

assert_contains() {
  local pattern="$1"
  if ! grep -Fq -- "$pattern" "$OUT_FILE"; then
    echo "[FAIL] missing output: $pattern" >&2
    cat "$OUT_FILE" >&2
    exit 1
  fi
}

assert_contains "[1/6]"
assert_contains "[2/6]"
assert_contains "[3/6]"
assert_contains "PostgreSQL: 127.0.0.1:25432 -> 127.0.0.1:15432"
assert_contains "Redis:      127.0.0.1:26379 -> 127.0.0.1:16379"
assert_contains "SPRING_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:25432/soda_dev"
assert_contains "REDIS_HOST=127.0.0.1"
assert_contains "REDIS_PORT=26379"
assert_contains "bootJar --no-daemon"
assert_contains "java.exe -Dserver.port="

echo "[PASS] be-dev-run dry-run contract verified"
