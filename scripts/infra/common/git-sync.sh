#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:?repository path is required}"
shift

if [[ "$#" -eq 0 ]]; then
  echo "At least one branch candidate is required" >&2
  exit 1
fi

REMOTE_URL="${GIT_SYNC_REMOTE_URL:-}"

mkdir -p "$REPO_DIR"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  if [[ -z "$REMOTE_URL" ]]; then
    echo "GIT_SYNC_REMOTE_URL is required to initialize $REPO_DIR" >&2
    exit 1
  fi

  git init "$REPO_DIR" >/dev/null
  git -C "$REPO_DIR" remote add origin "$REMOTE_URL"
fi

git config --global credential.helper store
git config --global --add safe.directory "$REPO_DIR" >/dev/null 2>&1 || true

cd "$REPO_DIR"
if [[ -n "$REMOTE_URL" ]]; then
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$REMOTE_URL"
  else
    git remote add origin "$REMOTE_URL"
  fi
fi
git fetch origin --prune
git reset --hard
git clean -fd

for branch in "$@"; do
  [[ -n "$branch" ]] || continue

  if git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    if git show-ref --verify --quiet "refs/heads/$branch"; then
      git checkout -f "$branch"
    else
      git checkout -f -B "$branch" "origin/$branch"
    fi

    git reset --hard "origin/$branch"
    exit 0
  fi
done

echo "No matching remote branch found for: $*" >&2
exit 1
