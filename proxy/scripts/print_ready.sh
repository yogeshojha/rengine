#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

print_ready_message() {
  load_env_domain
  local domain="${DOMAIN_NAME:-localhost}"
  echo ""
  log "=========================================="
  log " reNgine + Urban Proxy module is running"
  log "=========================================="
  log " Web UI:  https://${domain}/"
  log "         (or http://127.0.0.1:8000 if nginx not used)"
  log " Proxy file: $PROXY_FILE"
  if [[ -f "$PROXY_FILE" ]]; then
    local count
    count="$(grep -cE '^https?://' "$PROXY_FILE" 2>/dev/null || echo 0)"
    log " Proxies in file: $count"
  fi
  log " Sidecar logs: make logs"
  log " Status:       make status"
  log " Stop proxy:   make down"
  log " Stop all:     make down-all"
  echo ""
}
