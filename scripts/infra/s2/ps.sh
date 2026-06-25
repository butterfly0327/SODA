#!/usr/bin/env bash
set -euo pipefail

print_jenkins_job_status() {
  local job_name="$1"
  local script
  script="latest=\$(ls -1d /var/jenkins_home/jobs/${job_name}/builds/[0-9]* 2>/dev/null | sort -V | tail -n 1); if [ -z \"\$latest\" ]; then echo '${job_name}: no builds'; exit 0; fi; number=\$(basename \"\$latest\"); if grep -a -q '<building>true</building>' \"\$latest/build.xml\"; then echo '${job_name}: #'\"\$number\"' BUILDING'; exit 0; fi; result=\$(grep -a -m1 '<result>' \"\$latest/build.xml\" | sed -E 's/.*<result>([^<]+).*/\\1/' || true); [ -n \"\$result\" ] || result=UNKNOWN; echo '${job_name}: #'\"\$number\"' '\"\$result\""
  if ! docker exec jenkins-prod sh -lc "$script" 2>/dev/null; then
    echo "${job_name}: unavailable"
  fi
}

infra_pattern='^(jenkins-prod|prometheus-prod|grafana-prod|loki-prod|promtail-prod|cadvisor-prod|alertmanager-prod|blackbox-exporter|node-exporter-s2)	'
async_pattern='^(rabbitmq-prod|celery-worker-prod|celery-beat-prod)	'

echo "[infra]"
printf 'NAMES\tSTATUS\tPORTS\n'
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | {
  grep -E "$infra_pattern" || true
}

echo
echo "[async]"
printf 'NAMES\tSTATUS\tPORTS\n'
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | {
  grep -E "$async_pattern" || true
}

echo
echo "[jenkins]"
print_jenkins_job_status "soda-dev-pipeline"
print_jenkins_job_status "soda-prod-pipeline"

echo "S2 prod worker/monitoring/ci stack status listed"
