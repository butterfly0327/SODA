#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

bash "$ROOT_DIR/scripts/infra/common/bootstrap-networks.sh"
docker compose -f "$ROOT_DIR/infra/docker-compose.worker.prod.yml" up -d \
  prometheus-prod \
  grafana-prod \
  loki-prod \
  promtail-prod \
  cadvisor-prod \
  alertmanager-prod \
  blackbox-exporter \
  node-exporter-s2

echo "S2 prod monitoring stack startup commands completed"
