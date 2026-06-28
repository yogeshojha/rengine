#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

start_proxy_module() {
  mkdir -p "$DATA_DIR"
  log "Starting urban-proxy-fetcher..."
  compose up -d --build urban-proxy-fetcher

  log "Recreating celery to apply proxy volume mount..."
  compose up -d --force-recreate celery
}
