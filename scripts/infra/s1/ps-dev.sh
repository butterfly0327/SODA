#!/usr/bin/env bash
set -euo pipefail

pattern='^(dev-frontend|dev-spring|fastapi-dev|dev-postgres|dev-redis|minio|rabbitmq|celery-worker|celery-beat)	'

printf 'NAMES\tSTATUS\tPORTS\n'
sudo docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | {
  grep -E "$pattern" || true
}

echo "S1 dev stack status listed"
