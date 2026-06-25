#!/usr/bin/env bash
set -euo pipefail

pattern='^(rabbitmq-prod|celery-worker-prod|celery-beat-prod)	'

printf 'NAMES\tSTATUS\tPORTS\n'
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | {
  grep -E "$pattern" || true
}

echo "S2 prod async services status listed"
