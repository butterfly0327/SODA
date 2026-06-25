#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.prod.yml" up -d --build jenkins-prod
JENKINS_CONTAINER_NAME=jenkins-prod \
JENKINS_URL=http://127.0.0.1:18080/jenkins \
JENKINS_PUBLIC_URL=https://j14e105.p.ssafy.io/jenkins \
bash "$ROOT_DIR/scripts/infra/s2/bootstrap-jenkins-jobs.sh"

echo "S2 prod CI stack startup commands completed"
