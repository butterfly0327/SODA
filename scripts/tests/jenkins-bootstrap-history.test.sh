#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_SCRIPT="$ROOT_DIR/scripts/infra/s2/bootstrap-jenkins-jobs.sh"

test -f "$BOOTSTRAP_SCRIPT"

! rg -Fq 'doDelete' "$BOOTSTRAP_SCRIPT"
! rg -Fq '/job/$job_name/config.xml' "$BOOTSTRAP_SCRIPT"
rg -Fq 'updateByXml' "$BOOTSTRAP_SCRIPT"
rg -Fq 'createProjectFromXML' "$BOOTSTRAP_SCRIPT"
rg -Fq 'Updated existing Jenkins job:' "$BOOTSTRAP_SCRIPT"
rg -Fq 'Created Jenkins job:' "$BOOTSTRAP_SCRIPT"
rg -Fq '<org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>' "$BOOTSTRAP_SCRIPT"
rg -Fq '<org.jenkinsci.plugins.gwt.GenericTrigger plugin="generic-webhook-trigger@2.4.1">' "$BOOTSTRAP_SCRIPT"
rg -Fq '<token>${escaped_trigger_token}</token>' "$BOOTSTRAP_SCRIPT"

echo "jenkins-bootstrap-history tests passed"
