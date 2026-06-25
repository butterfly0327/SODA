#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <callback-url> <redirect-url> <expected-statuses>" >&2
  echo "  expected-statuses: comma-separated list such as 401 or 400,401" >&2
  exit 1
}

matches_expected_status() {
  local actual_status="$1"
  local expected_statuses="$2"
  local expected
  IFS=',' read -r -a statuses <<< "$expected_statuses"

  for expected in "${statuses[@]}"; do
    if [[ "$actual_status" == "$expected" ]]; then
      return 0
    fi
  done

  return 1
}

CALLBACK_URL="${1:-}"
REDIRECT_URL="${2:-}"
EXPECTED_STATUSES="${3:-}"

if [[ -z "$CALLBACK_URL" || -z "$REDIRECT_URL" || -z "$EXPECTED_STATUSES" ]]; then
  usage
fi

RESPONSE_BODY_FILE="$(mktemp)"
trap 'rm -f "$RESPONSE_BODY_FILE"' EXIT

PAYLOAD="$(printf '{"code":"codex-invalid-auth-code","redirectUrl":"%s"}' "$REDIRECT_URL")"
HTTP_STATUS="$(curl -ksS -o "$RESPONSE_BODY_FILE" -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -X POST \
  "$CALLBACK_URL" \
  --data "$PAYLOAD")"

if ! matches_expected_status "$HTTP_STATUS" "$EXPECTED_STATUSES"; then
  echo "OAuth callback smoke failed: ${CALLBACK_URL} -> ${HTTP_STATUS} (expected ${EXPECTED_STATUSES})" >&2
  cat "$RESPONSE_BODY_FILE" >&2
  exit 1
fi

echo "${CALLBACK_URL} -> ${HTTP_STATUS}"

