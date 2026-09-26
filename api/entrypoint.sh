#!/bin/sh
set -e

# every package compose mounts from the host; a save in one reloads the api.
# `make check-lists` fails when this drifts from compose's &api-volumes.
RELOAD_DIRS="app shared tools stages reports interest mcp channels connectors toolbox"

if [ "${API_RELOAD:-true}" = "true" ]; then
    for dir in $RELOAD_DIRS; do
        set -- "$@" --reload-dir "/app/$dir"
    done
    exec uv run uvicorn app.main:app \
        --host 0.0.0.0 --port 8000 \
        --reload "$@" \
        --timeout-graceful-shutdown 2
fi

exec uv run uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers "${API_WORKERS:-4}" \
    --timeout-graceful-shutdown 10
