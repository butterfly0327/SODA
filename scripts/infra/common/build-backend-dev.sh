#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
GRADLE_BUILDER_IMAGE="${GRADLE_BUILDER_IMAGE:-gradle:8.14.4-jdk21-alpine}"

DOCKER_USER_ARGS=()
DOCKER_CMD=()
if command -v id >/dev/null 2>&1; then
  DOCKER_USER_ARGS=(-u "$(id -u):$(id -g)")
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command is required to build backend dev bootJar" >&2
  exit 1
fi

if docker version >/dev/null 2>&1; then
  DOCKER_CMD=(docker)
elif command -v sudo >/dev/null 2>&1 && sudo docker version >/dev/null 2>&1; then
  DOCKER_CMD=(sudo docker)
else
  echo "docker daemon is not reachable; check Docker Desktop/WSL integration first" >&2
  exit 1
fi

rm -rf "$BACKEND_DIR/build" "$BACKEND_DIR/.gradle"

"${DOCKER_CMD[@]}" run --rm \
  "${DOCKER_USER_ARGS[@]}" \
  -e GRADLE_USER_HOME=/tmp/.gradle \
  -v "$BACKEND_DIR:/workspace" \
  -w /workspace \
  "$GRADLE_BUILDER_IMAGE" \
  sh -lc 'chmod +x gradlew && ./gradlew --project-cache-dir /tmp/project-cache bootJar -x test --no-daemon'

echo "Backend dev bootJar build completed"
