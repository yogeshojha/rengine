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
