#!/usr/bin/env bash
# Recover from broken migration state (duplicate tables / sequences).
# Run from proxy/: ./scripts/recover-db.sh

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

require_docker
ensure_root_env
detect_compose_project_name

VOLUME="${COMPOSE_PROJECT_NAME}_postgres_data"

log "This stops the stack and deletes PostgreSQL volume: $VOLUME"
log "All reNgine scan data in the database will be lost."
if [[ "${1:-}" != "-y" ]]; then
  read -r -p "Continue? (y/N): " answer || true
  case "${answer:-}" in
    y|Y|yes|YES|Yes) ;;
    *) log "Aborted."; exit 0 ;;
  esac
fi

cd "$ROOT_DIR"
make down 2>/dev/null || docker compose down 2>/dev/null || true

if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  docker volume rm "$VOLUME"
  log "Removed volume $VOLUME"
else
  log "Volume $VOLUME not found (may already be removed)."
fi

log "Done. Run: cd proxy && make up"
