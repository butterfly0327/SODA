#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/scripts/infra/common/oauth-callback-smoke.sh"

PORT="$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"

SERVER_LOG="$(mktemp)"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -f "$SERVER_LOG"
}
trap cleanup EXIT

python3 - "$PORT" >"$SERVER_LOG" 2>&1 <<'PY' &
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

port = int(sys.argv[1])


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw_body)

        if self.path == "/ok" and payload.get("redirectUrl") == "http://localhost/callback":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":401,"message":"invalid auth code"}')
            return

        self.send_response(502)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":502,"message":"unexpected"}')

    def log_message(self, format, *args):
        return


HTTPServer(("127.0.0.1", port), Handler).serve_forever()
PY
SERVER_PID="$!"

for _ in $(seq 1 20); do
  if curl -sS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

"$SCRIPT_PATH" "http://127.0.0.1:$PORT/ok" "http://localhost/callback" "401"

if "$SCRIPT_PATH" "http://127.0.0.1:$PORT/fail" "http://localhost/callback" "401" >/dev/null 2>&1; then
  echo "expected smoke script to fail on unexpected status" >&2
  exit 1
fi

echo "oauth-callback-smoke tests passed"
