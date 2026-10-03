#!/bin/sh
# chromium for the scan tools: never root, sandboxed when the container allows it
set -eu

BROWSER=/usr/bin/chromium
RUN_AS=rengine

if [ "$(id -u)" -eq 0 ]; then
  prev=""
  for arg in "$@"; do
    dir=""
    case "$arg" in
      --user-data-dir=*) dir="${arg#--user-data-dir=}" ;;
      *) [ "$prev" = "--user-data-dir" ] && dir="$arg" ;;
    esac
    if [ -n "$dir" ]; then
      mkdir -p "$dir"
      chown -R "$RUN_AS:$RUN_AS" "$dir"
    fi
    prev="$arg"
  done
  home="$(getent passwd "$RUN_AS" | cut -d: -f6)"
  exec setpriv --reuid="$RUN_AS" --regid="$RUN_AS" --init-groups \
    --inh-caps=-all --bounding-set=-all --no-new-privs \
    env HOME="$home" "$0" "$@"
fi

# a failed probe is not remembered
proven="${HOME:-/tmp}/.cache/chromium-sandboxed"

sandboxed() {
  [ -f "$proven" ] && return 0
  probe="$(mktemp -d)"
  if timeout 30 "$BROWSER" --headless --disable-gpu --no-first-run \
    --user-data-dir="$probe" --dump-dom about:blank >/dev/null 2>&1; then
    rm -rf "$probe"
    mkdir -p "$(dirname "$proven")"
    touch "$proven"
    return 0
  fi
  rm -rf "$probe"
  echo "chromium sandbox unavailable in this container, running without it" >&2
  return 1
}

if sandboxed; then
  for arg in "$@"; do
    shift
    [ "$arg" = "--no-sandbox" ] || set -- "$@" "$arg"
  done
else
  set -- --no-sandbox "$@"
fi

exec "$BROWSER" "$@"
