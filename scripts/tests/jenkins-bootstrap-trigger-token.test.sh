#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_SCRIPT="$ROOT_DIR/scripts/infra/s2/bootstrap-jenkins-jobs.sh"

test -f "$BOOTSTRAP_SCRIPT"

! rg -Fq 'JENKINS_DEV_TRIGGER_TOKEN="${JENKINS_DEV_TRIGGER_TOKEN:-soda-dev-trigger}"' "$BOOTSTRAP_SCRIPT"
! rg -Fq 'JENKINS_PROD_TRIGGER_TOKEN="${JENKINS_PROD_TRIGGER_TOKEN:-soda-prod-trigger}"' "$BOOTSTRAP_SCRIPT"
rg -Fq 'JENKINS_DEV_TRIGGER_TOKEN="${JENKINS_DEV_TRIGGER_TOKEN:-}"' "$BOOTSTRAP_SCRIPT"
rg -Fq 'JENKINS_PROD_TRIGGER_TOKEN="${JENKINS_PROD_TRIGGER_TOKEN:-}"' "$BOOTSTRAP_SCRIPT"
rg -Fq 'JENKINS_DEV_TRIGGER_TOKEN must be set' "$BOOTSTRAP_SCRIPT"
rg -Fq 'JENKINS_PROD_TRIGGER_TOKEN must be set' "$BOOTSTRAP_SCRIPT"

echo "jenkins-bootstrap-trigger-token tests passed"
