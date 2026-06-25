#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.prod"
S1_HOST_DEFAULT="j14e105.p.ssafy.io"
S2_HOST_DEFAULT="j14e105a.p.ssafy.io"

read_env_key() {
  local key="$1"
  local file="$2"
  local line

  [[ -f "$file" ]] || return 1
  line="$(grep -m1 "^${key}=" "$file" 2>/dev/null || true)"
  [[ -n "$line" ]] || return 1
  printf '%s\n' "${line#*=}"
}

S1_HOST="${STATUS_S1_HOST:-$(read_env_key S1_DEPLOY_HOST "$ENV_FILE" || printf '%s' "$S1_HOST_DEFAULT")}"
S2_HOST="${STATUS_S2_HOST:-$S2_HOST_DEFAULT}"
STATUS_SSH_USER="${STATUS_SSH_USER:-ubuntu}"
STATUS_SSH_KEY_PATH="${STATUS_SSH_KEY_PATH:-$HOME/.ssh/soda-status.pem}"

ssh_base_cmd() {
  local -a cmd=(ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new)
  if [[ -f "$STATUS_SSH_KEY_PATH" ]]; then
    cmd+=(-i "$STATUS_SSH_KEY_PATH")
  fi
  printf '%s\n' "${cmd[@]}"
}

run_remote_repo_script() {
  local host="$1"
  local script_path="$2"
  local remote_cmd
  local -a ssh_cmd
  remote_cmd="for d in /home/ubuntu/soda-prod /home/ubuntu/soda; do if [ -d \"\$d/scripts/infra\" ]; then cd \"\$d\"; break; fi; done; bash '$script_path'"
  mapfile -t ssh_cmd < <(ssh_base_cmd)
  "${ssh_cmd[@]}" "${STATUS_SSH_USER}@${host}" "$remote_cmd"
}

has_local_s1() {
  sudo docker ps --format '{{.Names}}' 2>/dev/null | grep -Eq '^(nginx|dev-spring|prod-frontend|spring-blue|spring-green|fastapi-prod|fastapi-dev)$'
}

has_local_s2() {
  docker ps --format '{{.Names}}' 2>/dev/null | grep -Eq '^(jenkins-prod|rabbitmq-prod|prometheus-prod|grafana-prod|loki-prod|alertmanager-prod|blackbox-exporter|node-exporter-s2|celery-worker-prod|celery-beat-prod)$'
}

print_managed_status() {
  local pg_host pg_port redis_host redis_port s3_endpoint s3_bucket use_pg use_redis use_s3 s3_region bucket_host bucket_code

  use_pg="$(read_env_key USE_MANAGED_POSTGRES "$ENV_FILE" || true)"
  use_redis="$(read_env_key USE_MANAGED_REDIS "$ENV_FILE" || true)"
  use_s3="$(read_env_key USE_MANAGED_S3 "$ENV_FILE" || true)"
  pg_host="$(read_env_key PROD_RDS_HOST "$ENV_FILE" || true)"
  pg_port="$(read_env_key PROD_RDS_PORT "$ENV_FILE" || printf '5432')"
  redis_host="$(read_env_key PROD_ELASTICACHE_HOST "$ENV_FILE" || true)"
  redis_port="$(read_env_key PROD_ELASTICACHE_PORT "$ENV_FILE" || printf '6379')"
  s3_endpoint="$(read_env_key S3_ENDPOINT "$ENV_FILE" || true)"
  s3_bucket="$(read_env_key S3_BUCKET "$ENV_FILE" || true)"
  s3_region="$(read_env_key S3_REGION "$ENV_FILE" || true)"

  echo "[aws-managed]"

  if [[ "$use_pg" == "true" && -n "$pg_host" ]]; then
    python3 - <<PY
import socket
host = ${pg_host@Q}
port = int(${pg_port@Q})
s = socket.socket()
s.settimeout(5)
try:
    s.connect((host, port))
    print(f"rds: {host}:{port} reachable")
except Exception as exc:
    print(f"rds: {host}:{port} unreachable ({exc})")
finally:
    s.close()
PY
  else
    echo "rds: not configured"
  fi

  if [[ "$use_redis" == "true" && -n "$redis_host" ]]; then
    python3 - <<PY
import socket
host = ${redis_host@Q}
port = int(${redis_port@Q})
s = socket.socket()
s.settimeout(5)
try:
    s.connect((host, port))
    print(f"elasticache: {host}:{port} reachable")
except Exception as exc:
    print(f"elasticache: {host}:{port} unreachable ({exc})")
finally:
    s.close()
PY
  else
    echo "elasticache: not configured"
  fi

  if [[ "$use_s3" == "true" && -n "$s3_endpoint" ]]; then
    echo "s3-endpoint: $(curl -ksS -o /dev/null -w '%{http_code}' "$s3_endpoint" || printf 'unreachable')"
    if [[ -n "$s3_bucket" && -n "$s3_region" ]]; then
      bucket_host="https://${s3_bucket}.s3.${s3_region}.amazonaws.com"
      bucket_code="$(curl -ksS -o /dev/null -w '%{http_code}' "$bucket_host" || printf 'unreachable')"
      echo "s3-bucket: ${bucket_host} -> ${bucket_code}"
    else
      echo "s3-bucket: not configured"
    fi
  else
    echo "s3: not configured"
  fi
}

print_s1_dev() {
  echo "[s1-dev]"
  if has_local_s1; then
    bash "$ROOT_DIR/scripts/infra/s1/ps-dev.sh"
  elif run_remote_repo_script "$S1_HOST" "scripts/infra/s1/ps-dev.sh"; then
    :
  else
    echo "S1 dev status unavailable (SSH key/path or network issue)"
  fi
}

print_s1_prod() {
  echo "[s1-prod]"
  if has_local_s1; then
    bash "$ROOT_DIR/scripts/infra/s1/ps-prod.sh"
  elif run_remote_repo_script "$S1_HOST" "scripts/infra/s1/ps-prod.sh"; then
    :
  else
    echo "S1 prod status unavailable (SSH key/path or network issue)"
  fi
}

print_s2() {
  echo "[s2]"
  if has_local_s2; then
    bash "$ROOT_DIR/scripts/infra/s2/ps.sh"
  elif run_remote_repo_script "$S2_HOST" "scripts/infra/s2/ps.sh"; then
    :
  else
    echo "S2 status unavailable (set STATUS_SSH_KEY_PATH to a key that can access ${S2_HOST})"
  fi
}

echo "=============================================="
echo "  SODA Stack Status"
echo "=============================================="
echo
print_managed_status
echo
print_s1_dev
echo
print_s1_prod
echo
print_s2
