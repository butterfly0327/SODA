#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SANITIZE_SCRIPT="$ROOT_DIR/scripts/infra/common/sanitize-remote-worktree.sh"
UP_DEV_SCRIPT="$ROOT_DIR/scripts/infra/s1/up-dev.sh"
JENKINSFILE_DEV="$ROOT_DIR/infra/jenkins/Jenkinsfile.dev"

test -x "$SANITIZE_SCRIPT"

owner_of() {
  if stat -f '%Su' "$1" >/dev/null 2>&1; then
    stat -f '%Su' "$1"
    return
  fi
  stat -c '%U' "$1"
}

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p \
  "$TMP_DIR/backend/src/__pycache__" \
  "$TMP_DIR/frontend/src" \
  "$TMP_DIR/data-platform/api/app/__pycache__"

touch "$TMP_DIR/frontend/src/keep.ts"
touch \
  "$TMP_DIR/backend/src/filter-owned.ts" \
  "$TMP_DIR/backend/src/__pycache__/stale.pyc" \
  "$TMP_DIR/data-platform/api/app/__pycache__/main.cpython-312.pyc"

"$SANITIZE_SCRIPT" "$TMP_DIR" "$(id -un)" "$(id -gn)" "$(id -un)"

test -e "$TMP_DIR/backend/src/filter-owned.ts"
test "$(owner_of "$TMP_DIR/backend/src/filter-owned.ts")" = "$(id -un)"
test ! -e "$TMP_DIR/backend/src/__pycache__/stale.pyc"
test ! -e "$TMP_DIR/data-platform/api/app/__pycache__/main.cpython-312.pyc"
test -e "$TMP_DIR/frontend/src/keep.ts"

rg -q 'compose_up_force_recreate_service "frontend dev stack" dev-frontend' "$UP_DEV_SCRIPT"
rg -q 'compose_up "data-platform dev stack"' "$UP_DEV_SCRIPT"
rg -q 'compose_up_force_recreate_service "data-platform dev app" fastapi-dev' "$UP_DEV_SCRIPT"
! rg -q '\$WORKSPACE/scripts/infra/common/' "$JENKINSFILE_DEV"
rg -q 'syncLocalRepo\(' "$JENKINSFILE_DEV"
rg -q 'def localProjectRoot\(\)' "$JENKINSFILE_DEV"
! rg -q "stage\\('Configure Webhook Trigger'\\)" "$JENKINSFILE_DEV"
rg -q "GITLAB_REPO_CREDENTIALS_ID = 'gitlab-repo-read'" "$JENKINSFILE_DEV"
rg -q 'withCredentials\(\[usernamePassword\(credentialsId: env\.GITLAB_REPO_CREDENTIALS_ID, usernameVariable: .GIT_REPO_USER., passwordVariable: .GIT_REPO_PASS.' "$JENKINSFILE_DEV"
rg -Fq 'cat > "$HOME/.git-credentials" <<EOF' "$JENKINSFILE_DEV"
rg -Fq 'https://${GIT_REPO_USER}:${GIT_REPO_PASS}@lab.ssafy.com' "$JENKINSFILE_DEV"
rg -Fq 'git config --global credential.helper store' "$JENKINSFILE_DEV"
rg -Fq 'for i in \$(seq 1 30); do' "$JENKINSFILE_DEV"
rg -Fq "rabbitmq_status=\\$(sudo docker inspect --format='{{.State.Status}}' rabbitmq 2>/dev/null || true)" "$JENKINSFILE_DEV"
rg -Fq "rabbitmq_health=\\$(sudo docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' rabbitmq 2>/dev/null || true)" "$JENKINSFILE_DEV"
rg -Fq 'sudo docker logs --tail 100 rabbitmq || true' "$JENKINSFILE_DEV"

sanitize_line="$(rg -n 'sanitizeRemoteWorktree\(localRepoPath, env\.S1_PROJECT_ROOT, env\.S1_DEPLOY_USER\)' "$JENKINSFILE_DEV" | cut -d: -f1)"
sync_line="$(rg -n 'syncRemoteRepo\(env\.S1_PROJECT_ROOT, \[env\.GIT_BRANCH_NAME, .develop.' "$JENKINSFILE_DEV" | cut -d: -f1)"
local_sync_line="$(rg -n 'syncLocalRepo\(localRepoPath, \[env\.GIT_BRANCH_NAME, .develop.' "$JENKINSFILE_DEV" | cut -d: -f1)"
credential_line="$(rg -n 'withCredentials\(\[usernamePassword\(credentialsId: env\.GITLAB_REPO_CREDENTIALS_ID' "$JENKINSFILE_DEV" | cut -d: -f1)"
test -n "$sanitize_line"
test -n "$sync_line"
test -n "$local_sync_line"
test -n "$credential_line"
test "$credential_line" -lt "$local_sync_line"
test "$local_sync_line" -lt "$sanitize_line"
test "$sanitize_line" -lt "$sync_line"

echo "dev-deploy-guardrails tests passed"
