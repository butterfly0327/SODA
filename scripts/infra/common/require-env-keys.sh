#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <env-file> <KEY|ALT_KEY> [<KEY|ALT_KEY> ...]" >&2
  exit 1
}

read_env_value() {
  local env_file="$1"
  local key="$2"
  local line

  line="$(grep -m1 "^${key}=" "$env_file" 2>/dev/null || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi

  printf '%s\n' "${line#*=}"
}

has_non_empty_value() {
  local value="$1"
  [[ -n "${value//[[:space:]]/}" ]]
}

validate_required_spec() {
  local env_file="$1"
  local spec="$2"
  local value
  local key
  IFS='|' read -r -a keys <<< "$spec"

  for key in "${keys[@]}"; do
    value="$(read_env_value "$env_file" "$key" || true)"
    if has_non_empty_value "$value"; then
      return 0
    fi
  done

  echo "Missing required non-empty key in ${env_file}: ${spec}" >&2
  return 1
}

ENV_FILE="${1:-}"
shift || true

if [[ -z "$ENV_FILE" || "$#" -eq 0 ]]; then
  usage
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file does not exist: $ENV_FILE" >&2
  exit 1
fi

for spec in "$@"; do
  validate_required_spec "$ENV_FILE" "$spec"
done

