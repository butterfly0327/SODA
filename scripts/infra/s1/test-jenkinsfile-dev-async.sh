#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
JENKINSFILE="$ROOT_DIR/infra/jenkins/Jenkinsfile.dev"

grep -F "up-async-dev.sh" "$JENKINSFILE" >/dev/null
grep -F "celery-roundtrip-smoke.sh" "$JENKINSFILE" >/dev/null
grep -F "celery-worker" "$JENKINSFILE" >/dev/null
grep -F "celery-beat" "$JENKINSFILE" >/dev/null
grep -F "rabbitmq" "$JENKINSFILE" >/dev/null

echo "PASS: Jenkins dev pipeline deploys and checks dev async services"
