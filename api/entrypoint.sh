#!/bin/sh
set -e

if [ "${API_RELOAD:-true}" = "true" ]; then
    exec uv run uvicorn app.main:app \
        --host 0.0.0.0 --port 8000 \
        --reload \
        --reload-dir /app/app \
        --reload-dir /app/shared \
        --reload-dir /app/tools \
        --reload-dir /app/stages \
        --reload-dir /app/reports \
        --reload-dir /app/toolbox \
        --timeout-graceful-shutdown 2
fi

exec uv run uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers "${API_WORKERS:-4}" \
    --timeout-graceful-shutdown 10
