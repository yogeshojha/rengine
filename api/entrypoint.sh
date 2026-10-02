#!/bin/sh
set -e

RELOAD_DIRS="app shared tools stages reports interest mcp channels connectors toolbox"
PROXIES="${TRUSTED_PROXIES:-127.0.0.1}"

if [ "${API_RELOAD:-true}" = "true" ]; then
    for dir in $RELOAD_DIRS; do
        set -- "$@" --reload-dir "/app/$dir"
    done
    exec uv run uvicorn app.main:app \
        --host 0.0.0.0 --port 8000 \
        --forwarded-allow-ips "$PROXIES" \
        --reload "$@" \
        --timeout-graceful-shutdown 2
fi

exec uv run uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --forwarded-allow-ips "$PROXIES" \
    --workers "${API_WORKERS:-4}" \
    --timeout-graceful-shutdown 10
