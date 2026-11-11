#!/usr/bin/env bash
set -Eeuo pipefail

: "${PORT:?Hostless must provide PORT}"

temporal server start-dev \
  --ip 127.0.0.1 \
  --port 7233 \
  --headless \
  --db-filename /tmp/temporal.db &
temporal_pid=$!
children=("$temporal_pid")

stop_children() {
  trap - EXIT INT TERM
  if ((${#children[@]})); then
    kill "${children[@]}" 2>/dev/null || true
    wait "${children[@]}" 2>/dev/null || true
  fi
}
trap stop_children EXIT
trap 'exit 0' INT TERM

ready=false
for _ in $(seq 1 60); do
  if temporal operator cluster health --address 127.0.0.1:7233 >/dev/null 2>&1; then
    ready=true
    break
  fi
  if ! kill -0 "$temporal_pid" 2>/dev/null; then
    wait "$temporal_pid"
    exit 1
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo "Temporal did not become healthy within 60 seconds" >&2
  exit 1
fi

alembic upgrade head

python -m syncally.workflows.worker &
children+=("$!")
python -m syncally.cli.outbox_worker &
children+=("$!")
python -m syncally.cli.payment_worker &
children+=("$!")
python -m syncally.cli.slack_events_worker &
children+=("$!")
uvicorn syncally.api.main:app --host 0.0.0.0 --port "$PORT" --limit-concurrency 16 &
children+=("$!")

set +e
wait -n "${children[@]}"
status=$?
set -e
exit "$status"
