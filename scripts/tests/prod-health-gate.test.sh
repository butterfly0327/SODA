#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
JENKINSFILE_PROD="$ROOT_DIR/infra/jenkins/Jenkinsfile.prod"

test -f "$JENKINSFILE_PROD"

rg -Fq 'for i in \$(seq 1 60); do' "$JENKINSFILE_PROD"
rg -Fq 'rag_exec_ready=false' "$JENKINSFILE_PROD"
rg -Fq "sudo docker exec fastapi-prod python -c 'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8083/v1/health\")'" "$JENKINSFILE_PROD"
rg -Fq '[ "\$rag_health" = "healthy" ] || [ "\$rag_exec_ready" = "true" ]' "$JENKINSFILE_PROD"
rg -Fq "sudo docker inspect fastapi-prod --format '{{range .State.Health.Log}}" "$JENKINSFILE_PROD"
! rg -Fq '$WORKSPACE/scripts/infra/common/' "$JENKINSFILE_PROD"
rg -Fq '$PROJECT_ROOT/scripts/infra/common/require-env-keys.sh' "$JENKINSFILE_PROD"
rg -Fq '$PROJECT_ROOT/scripts/infra/common/oauth-callback-smoke.sh' "$JENKINSFILE_PROD"
! rg -Fq "stage('Configure Webhook Trigger')" "$JENKINSFILE_PROD"

echo "prod-health-gate tests passed"
