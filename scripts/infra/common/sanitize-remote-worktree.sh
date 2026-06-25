#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="${1:?repository path is required}"
OWNER_NAME="${2:?owner name is required}"
OWNER_GROUP="${3:-$OWNER_NAME}"
OWNER_FILTER="${4:-root}"

SOURCE_DIRS=(
  "$REPO_PATH/backend/src"
  "$REPO_PATH/frontend/src"
  "$REPO_PATH/data-platform/api/app"
)

for source_dir in "${SOURCE_DIRS[@]}"; do
  if [[ ! -e "$source_dir" ]]; then
    continue
  fi

  find "$source_dir" -user "$OWNER_FILTER" -exec chown "${OWNER_NAME}:${OWNER_GROUP}" {} +
  find "$source_dir" \( -type d -name __pycache__ -o -type f -name '*.pyc' -o -type f -name '*.pyo' \) -exec rm -rf {} +
done
