#!/usr/bin/env bash
set -euo pipefail

NETWORKS=(prod-net dev-net common-net monitoring-net ci-net)

for net in "${NETWORKS[@]}"; do
  docker network inspect "$net" >/dev/null 2>&1 || docker network create "$net"
done

echo "Infra external networks are ready"
