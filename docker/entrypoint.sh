#!/usr/bin/env sh
set -eu

stop_children() {
  if [ -n "${WEB_PID:-}" ]; then
    kill "$WEB_PID" 2>/dev/null || true
  fi
  if [ -n "${API_PID:-}" ]; then
    kill "$API_PID" 2>/dev/null || true
  fi
  if [ -n "${WORKER_PID:-}" ]; then
    kill "$WORKER_PID" 2>/dev/null || true
  fi
}

wait_for_child() {
  while :; do
    for pid in ${WORKER_PID:-} ${API_PID:-} ${WEB_PID:-}; do
      if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        wait "$pid" 2>/dev/null || return 1
        return 1
      fi
    done
    sleep 1
  done
}

run_up() {
  if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
    echo "error: DASHSCOPE_API_KEY is required for Suton v0.1.0 embedding" >&2
    exit 1
  fi

  mkdir -p "${UPLOAD_DIR:-/app/uploads}"
  export PYTHONPATH="${PYTHONPATH:-/app/backend}"

  /app/backend/.venv/bin/python /app/scripts/migrate.py

  /app/backend/.venv/bin/rq worker suton --url "${REDIS_URL}" &
  WORKER_PID="$!"

  /app/backend/.venv/bin/uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8000 &
  API_PID="$!"

  if [ -f /app/frontend/frontend/server.js ]; then
    node /app/frontend/frontend/server.js &
  else
    node /app/frontend/server.js &
  fi
  WEB_PID="$!"

  trap stop_children INT TERM
  set +e
  wait_for_child
  status="$?"
  set -e
  stop_children
  wait ${WORKER_PID:-} ${API_PID:-} ${WEB_PID:-} 2>/dev/null || true
  exit "$status"
}

cmd="${1:-up}"

case "$cmd" in
  up)
    run_up
    ;;
  api)
    exec /app/backend/.venv/bin/uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8000
    ;;
  worker)
    exec /app/backend/.venv/bin/rq worker suton --url "${REDIS_URL}"
    ;;
  web)
    if [ -f /app/frontend/frontend/server.js ]; then
      exec node /app/frontend/frontend/server.js
    fi
    exec node /app/frontend/server.js
    ;;
  migrate)
    exec /app/backend/.venv/bin/python /app/scripts/migrate.py
    ;;
  *)
    exec "$@"
    ;;
esac
