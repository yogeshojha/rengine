#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

bootstrap_rengine_full() {
  log "Bootstrapping full reNgine stack..."
  cd "$ROOT_DIR"

  if [[ ! -f "$ROOT_DIR/secrets/certs/rengine.pem" ]]; then
    log "Generating TLS certificates (make certs)..."
    make certs
  else
    log "TLS certificates found, skipping make certs."
  fi

  log "Building images (make build)..."
  make build

  log "Starting core services (make up)..."
  make up

  cd "$PROXY_DIR"
}

wait_for_web_migrations() {
  log "Waiting for web startup migrations (web/entrypoint.sh runs migrate)..."
  local i
  for i in $(seq 1 120); do
    if ! service_running web; then
      sleep 2
      continue
    fi
    if compose exec -T web python3 manage.py migrate --check >/dev/null 2>&1; then
      log "Database migrations are up to date."
      return 0
    fi
    sleep 2
  done
  log "Migration check timed out."
  log "Web may still be starting. If the UI fails, run: make -C .. migrate"
}

prompt_or_hint_username() {
  log "Create an admin account if you have not already:"
  log "  make -C .. username"
  if [[ "$NON_INTERACTIVE" == true ]]; then
    return 0
  fi
  read -r -p "Create superuser now? (y/N): " answer || true
  case "${answer:-}" in
    y|Y|yes|YES|Yes)
      cd "$ROOT_DIR"
      make username
      cd "$PROXY_DIR"
      ;;
    *)
      log "Skipped. Run 'make -C .. username' when ready."
      ;;
  esac
}
