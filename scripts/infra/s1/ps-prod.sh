#!/usr/bin/env bash
set -euo pipefail

pattern='^(nginx|promtail-s1|cadvisor-s1|node-exporter-s1|nginx-prometheus-exporter|prod-frontend|spring-blue|spring-green|fastapi-prod|codex-adapter-prod)	'

printf 'NAMES\tSTATUS\tPORTS\n'
sudo docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | {
  grep -E "$pattern" || true
}

echo "S1 prod stack status listed"
