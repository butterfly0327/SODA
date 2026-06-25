#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
ENV_FILE="${SODA_DEV_ENV_FILE:-$ROOT_DIR/.env.dev}"
SSH_HOST="${SODA_DEV_SSH_HOST:-j14e105.p.ssafy.io}"
SSH_USER="${SODA_DEV_SSH_USER:-ubuntu}"
SSH_KEY_PATH="${SODA_DEV_SSH_KEY_PATH:-$ROOT_DIR/J14E105T.pem}"
SSH_KEY_WORK_PATH=""
WINDOWS_SSH_KEY_PATH=""
TUNNEL_PID=""
WINDOWS_TUNNEL_PID=""

LOCAL_DB_PORT="${SODA_DEV_LOCAL_DB_PORT:-25432}"
LOCAL_REDIS_PORT="${SODA_DEV_LOCAL_REDIS_PORT:-26379}"
REMOTE_DB_PORT="${SODA_DEV_REMOTE_DB_PORT:-15432}"
REMOTE_REDIS_PORT="${SODA_DEV_REMOTE_REDIS_PORT:-16379}"
APP_PORT=""

DRY_RUN="${SODA_DEV_RUN_DRY_RUN:-0}"
RUNNER_MODE="${SODA_DEV_RUNNER:-auto}"
CONTROL_SOCKET="$(mktemp -u "${TMPDIR:-/tmp}/soda-dev-tunnel.XXXXXX.sock")"
PYTHON_BIN="$(command -v python3 || command -v python || true)"
WINDOWS_BACKEND_DIR=""
WINDOWS_RUN_CMD=()
LINUX_RUN_CMD=("./gradlew" "bootRun" "--no-daemon" "--console=plain")
LOADED_ENV_KEYS=()

step() {
  printf '\n[%s/6] %s\n' "$1" "$2"
}

note() {
  printf '      %s\n' "$1"
}

fail() {
  printf '[오류] %s\n' "$1" >&2
  exit 1
}

require_file() {
  local path="$1"
  local label="$2"
  [[ -f "$path" ]] || fail "${label} 파일을 찾을 수 없습니다: $path"
}

require_command() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "필수 명령을 찾을 수 없습니다: $cmd"
}

load_env_file() {
  local file="$1"
  local line key value

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key%$'\r'}"
    value="${value%$'\r'}"
    export "$key=$value"
    LOADED_ENV_KEYS+=("$key")
  done < "$file"
}

assert_local_port_available() {
  local port="$1"
  local label="$2"

  "$PYTHON_BIN" - "$port" "$label" <<'PY'
import socket
import sys

port = int(sys.argv[1])
label = sys.argv[2]

sock = socket.socket()
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    print(f"{label}용 로컬 포트가 이미 사용 중입니다: 127.0.0.1:{port}", file=sys.stderr)
    raise SystemExit(1)
finally:
    sock.close()
PY
}

is_local_port_available() {
  local port="$1"

  "$PYTHON_BIN" - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket()
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
PY
}

is_windows_port_available() {
  local port="$1"

  powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >/dev/null 2>&1
}

choose_local_port() {
  local requested_port="$1"
  local label="$2"
  local strict="${3:-0}"
  local candidate="$requested_port"
  local last_candidate="$requested_port"

  if [[ "$strict" == "1" ]]; then
    assert_local_port_available "$requested_port" "$label"
    printf '%s' "$requested_port"
    return 0
  fi

  for _ in $(seq 0 20); do
    if is_local_port_available "$candidate"; then
      printf '%s' "$candidate"
      return 0
    fi
    last_candidate="$candidate"
    candidate="$((candidate + 1))"
  done

  fail "${label}용 사용 가능한 로컬 포트를 찾지 못했습니다. 시작 포트: 127.0.0.1:${requested_port}, 마지막 확인 포트: ${last_candidate}"
}

choose_app_port() {
  local requested_port="$1"
  local strict="${2:-0}"
  local fallback_port="$((requested_port + 1))"

  if [[ "$RUNNER_MODE" != "windows" ]]; then
    if [[ "$strict" == "1" ]]; then
      choose_local_port "$requested_port" "Spring Boot 앱 포트" "$strict"
      return 0
    fi

    if is_local_port_available "$requested_port"; then
      printf '%s' "$requested_port"
      return 0
    fi

    if is_local_port_available "$fallback_port"; then
      printf '%s' "$fallback_port"
      return 0
    fi

    fail "Spring Boot 앱 포트가 모두 사용 중입니다. 확인한 포트: 127.0.0.1:${requested_port}, 127.0.0.1:${fallback_port}"
    return 0
  fi

  if [[ "$strict" == "1" ]]; then
    is_windows_port_available "$requested_port" || fail "Spring Boot 앱 포트가 이미 사용 중입니다: 127.0.0.1:${requested_port}"
    printf '%s' "$requested_port"
    return 0
  fi

  if is_windows_port_available "$requested_port"; then
    printf '%s' "$requested_port"
    return 0
  fi

  if is_windows_port_available "$fallback_port"; then
    printf '%s' "$fallback_port"
    return 0
  fi

  fail "Windows에서 Spring Boot 앱 포트가 모두 사용 중입니다. 확인한 포트: 127.0.0.1:${requested_port}, 127.0.0.1:${fallback_port}"
}

choose_tunnel_port() {
  local requested_port="$1"
  local label="$2"
  local strict="${3:-0}"
  local candidate="$requested_port"
  local last_candidate="$requested_port"

  if [[ "$RUNNER_MODE" != "windows" ]]; then
    choose_local_port "$requested_port" "$label" "$strict"
    return 0
  fi

  if [[ "$strict" == "1" ]]; then
    is_windows_port_available "$requested_port" || fail "${label}용 로컬 포트가 이미 사용 중입니다: 127.0.0.1:${requested_port}"
    printf '%s' "$requested_port"
    return 0
  fi

  for _ in $(seq 0 20); do
    if is_windows_port_available "$candidate"; then
      printf '%s' "$candidate"
      return 0
    fi
    last_candidate="$candidate"
    candidate="$((candidate + 1))"
  done

  fail "${label}용 사용 가능한 로컬 포트를 찾지 못했습니다. 시작 포트: 127.0.0.1:${requested_port}, 마지막 확인 포트: ${last_candidate}"
}

verify_tcp_endpoint() {
  local host="$1"
  local port="$2"
  local label="$3"

  "$PYTHON_BIN" - "$host" "$port" "$label" <<'PY'
import socket
import sys
import time

host = sys.argv[1]
port = int(sys.argv[2])
label = sys.argv[3]

last_error = None
for _ in range(15):
    sock = socket.socket()
    sock.settimeout(1.0)
    try:
        sock.connect((host, port))
    except OSError as exc:
        last_error = exc
        time.sleep(1)
    else:
        print(f"{label} 연결 확인 완료: {host}:{port}")
        raise SystemExit(0)
    finally:
        sock.close()

print(f"{label} 연결 확인 실패: {host}:{port} ({last_error})", file=sys.stderr)
raise SystemExit(1)
PY
}

verify_windows_tcp_endpoint() {
  local host="$1"
  local port="$2"
  local label="$3"

  powershell.exe -NoProfile -Command "\$deadline=(Get-Date).AddSeconds(15); while((Get-Date) -lt \$deadline){ try { \$client = New-Object Net.Sockets.TcpClient; \$iar = \$client.BeginConnect('${host}', ${port}, \$null, \$null); if(\$iar.AsyncWaitHandle.WaitOne(1000)){ \$client.EndConnect(\$iar); \$client.Close(); Write-Output '${label} 연결 확인 완료: ${host}:${port}'; exit 0 } \$client.Close() } catch { }; Start-Sleep -Seconds 1 }; Write-Error '${label} 연결 확인 실패: ${host}:${port}'; exit 1"
}

cleanup() {
  if [[ -S "$CONTROL_SOCKET" ]]; then
    ssh -S "$CONTROL_SOCKET" -O exit -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SSH_HOST}" >/dev/null 2>&1 || true
  fi
  if [[ "$RUNNER_MODE" == "windows" ]]; then
    powershell.exe -NoProfile -Command "Get-NetTCPConnection -LocalPort ${SERVER_PORT:-0} -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
    powershell.exe -NoProfile -Command "Get-NetTCPConnection -LocalPort ${LOCAL_DB_PORT:-0},${LOCAL_REDIS_PORT:-0} -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
  fi
  if [[ -n "$WINDOWS_TUNNEL_PID" ]]; then
    powershell.exe -NoProfile -Command "Stop-Process -Id ${WINDOWS_TUNNEL_PID} -Force -ErrorAction SilentlyContinue" >/dev/null 2>&1 || true
  fi
  if [[ -n "$TUNNEL_PID" ]]; then
    kill "$TUNNEL_PID" >/dev/null 2>&1 || true
  fi
  pkill -f "ssh .* -S $CONTROL_SOCKET" >/dev/null 2>&1 || true
  if [[ -n "$SSH_KEY_WORK_PATH" && -f "$SSH_KEY_WORK_PATH" ]]; then
    rm -f "$SSH_KEY_WORK_PATH"
  fi
  rm -f "$CONTROL_SOCKET"
}

handle_interrupt() {
  cleanup
  exit 130
}

append_wslenv_vars() {
  local existing="${WSLENV:-}"
  local -a entries=()
  local -a vars_to_add=("$@")
  local item base candidate found

  if [[ -n "$existing" ]]; then
    IFS=':' read -r -a entries <<< "$existing"
  fi

  for candidate in "${vars_to_add[@]}"; do
    found=0
    for item in "${entries[@]}"; do
      base="${item%%/*}"
      if [[ "$base" == "$candidate" ]]; then
        found=1
        break
      fi
    done
    if [[ "$found" -eq 0 ]]; then
      entries+=("$candidate")
    fi
  done

  local joined=""
  for item in "${entries[@]}"; do
    [[ -z "$item" ]] && continue
    if [[ -z "$joined" ]]; then
      joined="$item"
    else
      joined="${joined}:$item"
    fi
  done
  export WSLENV="$joined"
}

resolve_runner() {
  local mode="$RUNNER_MODE"

  if [[ "$mode" == "auto" ]]; then
    if command -v powershell.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
      mode="windows"
    elif command -v java >/dev/null 2>&1; then
      mode="linux"
    else
      fail "사용 가능한 Java 실행 환경을 찾지 못했습니다. WSL에 Java를 설치하거나, powershell.exe를 사용할 수 있는 Windows 환경에서 실행해 주세요."
    fi
  fi

  case "$mode" in
    linux)
      command -v java >/dev/null 2>&1 || fail "SODA_DEV_RUNNER=linux 설정은 PATH에 java가 있어야 합니다"
      note "실행 방식: Linux gradlew"
      ;;
    windows)
      require_command powershell.exe
      require_command wslpath
      require_command ssh.exe
      WINDOWS_BACKEND_DIR="$(wslpath -w "$BACKEND_DIR")"
      WINDOWS_SSH_KEY_PATH="$(wslpath -w "$SSH_KEY_PATH")"
      append_wslenv_vars \
        "${LOADED_ENV_KEYS[@]}" \
        DEV_POSTGRES_HOST \
        DEV_POSTGRES_PORT \
        REDIS_HOST \
        REDIS_PORT \
        SPRING_PROFILES_ACTIVE \
        SPRING_DATASOURCE_URL \
        SPRING_DATASOURCE_USERNAME \
        SPRING_DATASOURCE_PASSWORD \
        POSTGRES_URL \
        DATABASE_URL \
        SERVER_PORT
      WINDOWS_RUN_CMD=(
        powershell.exe
        -NoProfile
        -Command
        "\$javaCandidates = New-Object System.Collections.Generic.List[string]; if (\$env:JAVA_HOME_21_X64) { \$javaCandidates.Add((Join-Path \$env:JAVA_HOME_21_X64 'bin\\java.exe')) }; if (\$env:USERPROFILE) { \$jdks = Join-Path \$env:USERPROFILE '.jdks'; if (Test-Path \$jdks) { Get-ChildItem -Path \$jdks -Directory -ErrorAction SilentlyContinue | Where-Object { \$_.Name -match '(^|[^0-9])21([^0-9]|$)' } | Sort-Object Name -Descending | ForEach-Object { \$javaCandidates.Add((Join-Path \$_.FullName 'bin\\java.exe')) } } }; \$javaExe = \$javaCandidates | Where-Object { Test-Path \$_ } | Select-Object -First 1; if (-not \$javaExe) { Write-Error 'Java 21 runtime not found. Install JDK 21 or set JAVA_HOME_21_X64.'; exit 1 }; Set-Location -LiteralPath '${WINDOWS_BACKEND_DIR}'; & .\\gradlew.bat bootJar --no-daemon --console=plain; if (\$LASTEXITCODE -ne 0) { exit \$LASTEXITCODE }; \$jar = Get-ChildItem -Path .\\build\\libs\\*.jar | Where-Object { \$_.Name -notlike '*-plain.jar' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if (-not \$jar) { Write-Error 'Failed to locate Spring Boot jar under build\\libs'; exit 1 }; & \$javaExe ('-Dserver.port=' + \$env:SERVER_PORT) '-jar' \$jar.FullName"
      )
      note "실행 방식: Windows bootJar + java.exe"
      note "Windows backend 경로: ${WINDOWS_BACKEND_DIR}"
      note "Windows SSH 키 경로: ${WINDOWS_SSH_KEY_PATH}"
      note "Windows Java 21 후보: JAVA_HOME_21_X64 또는 %USERPROFILE%\\.jdks\\*21*"
      note "WSLENV를 통해 Windows로 환경변수를 전달합니다"
      ;;
    *)
      fail "지원하지 않는 SODA_DEV_RUNNER 값입니다: ${mode}"
      ;;
  esac

  RUNNER_MODE="$mode"
}

run_bootrun() {
  if [[ "$RUNNER_MODE" == "windows" ]]; then
    "${WINDOWS_RUN_CMD[@]}"
  else
    "${LINUX_RUN_CMD[@]}"
  fi
}

step 1 "환경 파일과 기본값 불러오기"
require_file "$ENV_FILE" ".env.dev"
require_file "$SSH_KEY_PATH" "SSH 개인키"
require_file "$BACKEND_DIR/gradlew" "Gradle wrapper"
load_env_file "$ENV_FILE"
note "env 파일: $ENV_FILE"
note "backend 경로: $BACKEND_DIR"
note "SSH 대상: ${SSH_USER}@${SSH_HOST}"
note "주의: 이 명령은 공유 S1 dev PostgreSQL/Redis를 사용하므로 공용 상태를 변경할 수 있습니다"

[[ -n "${DEV_POSTGRES_DB:-}" ]] || fail "$ENV_FILE 에 DEV_POSTGRES_DB 값이 필요합니다"
[[ -n "${DEV_POSTGRES_USER:-}" ]] || fail "$ENV_FILE 에 DEV_POSTGRES_USER 값이 필요합니다"
[[ -n "${DEV_POSTGRES_PASSWORD:-}" ]] || fail "$ENV_FILE 에 DEV_POSTGRES_PASSWORD 값이 필요합니다"
APP_PORT="${SODA_DEV_APP_PORT:-8080}"
export SERVER_PORT="$APP_PORT"

step 2 "로컬 도구와 포트 상태 확인"
require_command ssh
[[ -n "$PYTHON_BIN" ]] || fail "python3 또는 python 명령이 필요합니다"
resolve_runner
LOCAL_DB_PORT="$(choose_tunnel_port "$LOCAL_DB_PORT" "PostgreSQL 터널" "${SODA_DEV_LOCAL_DB_PORT+1}")"
LOCAL_REDIS_PORT="$(choose_tunnel_port "$LOCAL_REDIS_PORT" "Redis 터널" "${SODA_DEV_LOCAL_REDIS_PORT+1}")"
APP_PORT="$(choose_app_port "$APP_PORT" "${SODA_DEV_APP_PORT+1}")"
export SERVER_PORT="$APP_PORT"
note "로컬 PostgreSQL 포트 사용 가능: 127.0.0.1:${LOCAL_DB_PORT}"
note "로컬 Redis 포트 사용 가능:      127.0.0.1:${LOCAL_REDIS_PORT}"
note "로컬 Spring 포트 사용 가능:     127.0.0.1:${APP_PORT}"
if [[ "$RUNNER_MODE" == "windows" ]]; then
  note "Windows OpenSSH 터널을 사용합니다"
else
  SSH_KEY_WORK_PATH="$(mktemp "${TMPDIR:-/tmp}/soda-dev-key.XXXXXX")"
  cp "$SSH_KEY_PATH" "$SSH_KEY_WORK_PATH"
  chmod 600 "$SSH_KEY_WORK_PATH"
  note "권한을 조정한 SSH 키 복사본 사용: ${SSH_KEY_WORK_PATH}"
fi

if [[ "$RUNNER_MODE" != "windows" ]]; then
  SSH_CMD=(
    ssh
    -i "$SSH_KEY_WORK_PATH"
    -M
    -S "$CONTROL_SOCKET"
    -f
    -N
    -o BatchMode=yes
    -o ExitOnForwardFailure=yes
    -o StrictHostKeyChecking=accept-new
    -L "${LOCAL_DB_PORT}:127.0.0.1:${REMOTE_DB_PORT}"
    -L "${LOCAL_REDIS_PORT}:127.0.0.1:${REMOTE_REDIS_PORT}"
    "${SSH_USER}@${SSH_HOST}"
  )
else
  SSH_CMD=()
fi

export DEV_POSTGRES_HOST="127.0.0.1"
export DEV_POSTGRES_PORT="$LOCAL_DB_PORT"
export REDIS_HOST="127.0.0.1"
export REDIS_PORT="$LOCAL_REDIS_PORT"
export SPRING_PROFILES_ACTIVE="${SPRING_PROFILES_ACTIVE:-dev}"
export SPRING_DATASOURCE_URL="jdbc:postgresql://127.0.0.1:${LOCAL_DB_PORT}/${DEV_POSTGRES_DB}"
export SPRING_DATASOURCE_USERNAME="$DEV_POSTGRES_USER"
export SPRING_DATASOURCE_PASSWORD="$DEV_POSTGRES_PASSWORD"
export POSTGRES_URL="postgresql://${DEV_POSTGRES_USER}:${DEV_POSTGRES_PASSWORD}@127.0.0.1:${LOCAL_DB_PORT}/${DEV_POSTGRES_DB}"
export DATABASE_URL="$POSTGRES_URL"

if [[ "$DRY_RUN" == "1" ]]; then
  step 3 "SSH 터널 열기 (dry-run)"
  note "PostgreSQL: 127.0.0.1:${LOCAL_DB_PORT} -> 127.0.0.1:${REMOTE_DB_PORT}"
  note "Redis:      127.0.0.1:${LOCAL_REDIS_PORT} -> 127.0.0.1:${REMOTE_REDIS_PORT}"
  if [[ "$RUNNER_MODE" == "windows" ]]; then
    note "명령: ssh.exe -i ${WINDOWS_SSH_KEY_PATH} -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new -L 127.0.0.1:${LOCAL_DB_PORT}:127.0.0.1:${REMOTE_DB_PORT} -L 127.0.0.1:${LOCAL_REDIS_PORT}:127.0.0.1:${REMOTE_REDIS_PORT} ${SSH_USER}@${SSH_HOST}"
  else
    printf '      명령:'
    for arg in "${SSH_CMD[@]}"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  fi

  step 4 "터널 연결 확인 (dry-run)"
  note "실제 실행 시 PostgreSQL 터널에 TCP 연결 검사를 수행합니다"
  note "실제 실행 시 Redis 터널에 TCP 연결 검사를 수행합니다"

  step 5 "Spring 환경변수 주입 (dry-run)"
  note "SPRING_DATASOURCE_URL=${SPRING_DATASOURCE_URL}"
  note "SPRING_DATASOURCE_USERNAME=${SPRING_DATASOURCE_USERNAME}"
  note "REDIS_HOST=${REDIS_HOST}"
  note "REDIS_PORT=${REDIS_PORT}"
  note "SERVER_PORT=${SERVER_PORT}"

  step 6 "로컬 Spring bootRun 시작 (dry-run)"
  if [[ "$RUNNER_MODE" == "windows" ]]; then
    note "명령: powershell.exe -NoProfile -Command \"Set-Location -LiteralPath '${WINDOWS_BACKEND_DIR}'; & .\\gradlew.bat bootJar --no-daemon --console=plain; java.exe -Dserver.port=${SERVER_PORT} -jar build\\libs\\<boot-jar>.jar\""
  else
    note "명령: cd ${BACKEND_DIR} && ./gradlew bootRun --no-daemon --console=plain"
  fi
  exit 0
fi

trap cleanup EXIT
trap handle_interrupt INT TERM

step 3 "SSH 터널 열기"
note "PostgreSQL: 127.0.0.1:${LOCAL_DB_PORT} -> 127.0.0.1:${REMOTE_DB_PORT}"
note "Redis:      127.0.0.1:${LOCAL_REDIS_PORT} -> 127.0.0.1:${REMOTE_REDIS_PORT}"
if [[ "$RUNNER_MODE" == "windows" ]]; then
  WINDOWS_TUNNEL_PID="$(
    powershell.exe -NoProfile -Command "\$p = Start-Process -FilePath 'ssh.exe' -ArgumentList @('-i','${WINDOWS_SSH_KEY_PATH}','-N','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','StrictHostKeyChecking=accept-new','-L','127.0.0.1:${LOCAL_DB_PORT}:127.0.0.1:${REMOTE_DB_PORT}','-L','127.0.0.1:${LOCAL_REDIS_PORT}:127.0.0.1:${REMOTE_REDIS_PORT}','${SSH_USER}@${SSH_HOST}') -PassThru -WindowStyle Hidden; \$p.Id"
  )"
  note "Windows SSH 터널 PID: ${WINDOWS_TUNNEL_PID}"
else
  "${SSH_CMD[@]}"
  TUNNEL_PID="$(pgrep -f "ssh .* -S $CONTROL_SOCKET" | head -n 1 || true)"
  note "SSH 제어 소켓 준비 완료: $CONTROL_SOCKET"
fi

step 4 "터널 연결 확인"
if [[ "$RUNNER_MODE" == "windows" ]]; then
  verify_windows_tcp_endpoint "127.0.0.1" "$LOCAL_DB_PORT" "PostgreSQL 터널"
  verify_windows_tcp_endpoint "127.0.0.1" "$LOCAL_REDIS_PORT" "Redis 터널"
else
  verify_tcp_endpoint "127.0.0.1" "$LOCAL_DB_PORT" "PostgreSQL 터널"
  verify_tcp_endpoint "127.0.0.1" "$LOCAL_REDIS_PORT" "Redis 터널"
fi

step 5 "Spring 환경변수 주입"
note "SPRING_DATASOURCE_URL=${SPRING_DATASOURCE_URL}"
note "SPRING_DATASOURCE_USERNAME=${SPRING_DATASOURCE_USERNAME}"
note "REDIS_HOST=${REDIS_HOST}"
note "REDIS_PORT=${REDIS_PORT}"
note "SERVER_PORT=${SERVER_PORT}"

step 6 "로컬 Spring 시작"
note "작업 디렉터리: $BACKEND_DIR"
note "이 프로세스는 포그라운드 서버 태스크라서 Ctrl+C로 종료할 때까지 이 터미널에 붙어 있습니다"
cd "$BACKEND_DIR"
set +e
run_bootrun
run_status=$?
set -e
exit "$run_status"
