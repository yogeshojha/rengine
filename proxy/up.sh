#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/scripts/common.sh"

parse_args "$@"
require_docker
ensure_root_env
mkdir -p "$DATA_DIR"

if ! is_rengine_core_running; then
  log "reNgine core is not running — bootstrapping full stack..."
  source "$PROXY_DIR/scripts/bootstrap_rengine.sh"
  bootstrap_rengine_full
  wait_for_db_ready
  wait_for_web_migrations
  prompt_or_hint_username
else
  log "reNgine core already running — starting proxy module only."
fi

source "$PROXY_DIR/scripts/start_proxy_module.sh"
start_proxy_module

wait_for_proxy_file 300

source "$PROXY_DIR/scripts/print_ready.sh"
print_ready_message
