#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/scripts/infra/common/require-env-keys.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cat > "$TMP_DIR/valid.env" <<'EOF'
ALPHA=one
BETA=two
REDIRECT=https://example.com/callback
EOF

cat > "$TMP_DIR/missing.env" <<'EOF'
ALPHA=one
EOF

cat > "$TMP_DIR/blank.env" <<'EOF'
ALPHA=
EOF

"$SCRIPT_PATH" "$TMP_DIR/valid.env" ALPHA BETA 'REDIRECT|REDIRECTS'

if "$SCRIPT_PATH" "$TMP_DIR/missing.env" ALPHA BETA >/dev/null 2>&1; then
  echo "expected missing key validation to fail" >&2
  exit 1
fi

if "$SCRIPT_PATH" "$TMP_DIR/blank.env" ALPHA >/dev/null 2>&1; then
  echo "expected blank key validation to fail" >&2
  exit 1
fi

if "$SCRIPT_PATH" "$TMP_DIR/missing.env" 'REDIRECT|REDIRECTS' >/dev/null 2>&1; then
  echo "expected alternative key validation to fail when all options are missing" >&2
  exit 1
fi

echo "require-env-keys tests passed"
