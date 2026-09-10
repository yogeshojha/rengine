#!/usr/bin/env bash
# Back up a reNgine instance, or restore one.
#
#   scripts/backup.sh dump [DIR]     write a dated archive to DIR (default ./backups)
#   scripts/backup.sh restore FILE   replace this instance's data with an archive
#   scripts/backup.sh list [DIR]     what is in DIR
#
# What is in an archive, and why:
#   db.dump          the database, custom format so it restores in parallel
#   scan_media.tar   screenshots and captured responses, which live on disk not in pg
#   volumes.tar      uploaded wordlists, nuclei templates, report themes and fonts
#   env              the settings a restore needs, SECRET_KEY included
#
# SECRET_KEY is in the archive because API keys, proxy credentials and notification
# secrets are Fernet-encrypted with a key derived from it: restore without it and
# every stored secret is unreadable. Treat an archive as a credential.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

DEST="${2:-./backups}"
DB_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || echo rengine)"
DB_NAME="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2- || echo rengine)"
VOLUMES=(vuln_templates wordlists report_fonts reports_out)

WORK=""
cleanup() { [ -n "$WORK" ] && rm -rf "$WORK"; }
trap cleanup EXIT

say() { printf '\033[1m%s\033[0m\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

running() { docker compose ps --format '{{.Service}}' 2>/dev/null | grep -qx "$1"; }

dump() {
  running db || die "the db service is not running"
  mkdir -p "$DEST"
  local stamp archive work
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  archive="$DEST/rengine-$stamp.tar"
  WORK="$(mktemp -d)"; work="$WORK"

  say "database"
  docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$work/db.dump"

  say "scan media"
  tar -cf "$work/scan_media.tar" -C . scan_media 2>/dev/null || tar -cf "$work/scan_media.tar" -T /dev/null

  say "volumes"
  local vwork="$work/volumes"
  mkdir -p "$vwork"
  for volume in "${VOLUMES[@]}"; do
    docker run --rm -v "$(basename "$HERE")_$volume:/from" -v "$vwork:/to" alpine \
      sh -c "tar -cf /to/$volume.tar -C /from . 2>/dev/null || true" >/dev/null 2>&1 || true
  done
  tar -cf "$work/volumes.tar" -C "$vwork" .

  # only what a restore needs; nothing else from .env travels
  grep -E '^(SECRET_KEY|POSTGRES_|ADMIN_)' .env > "$work/env" || true

  tar -cf "$archive" -C "$work" db.dump scan_media.tar volumes.tar env
  say "wrote $archive ($(du -h "$archive" | cut -f1))"
}

restore() {
  local archive="${2:-}"
  [ -f "$archive" ] || die "usage: scripts/backup.sh restore FILE"
  running db || die "the db service is not running"

  printf 'This replaces the data in this instance. Type the database name (%s) to go on: ' "$DB_NAME"
  read -r answer
  [ "$answer" = "$DB_NAME" ] || die "not confirmed"

  local work
  WORK="$(mktemp -d)"; work="$WORK"
  tar -xf "$archive" -C "$work"

  say "stopping the workers so nothing writes during the restore"
  docker compose stop api worker-default worker-beat >/dev/null

  say "database"
  docker compose exec -T db psql -U "$DB_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" >/dev/null
  docker compose exec -T db dropdb -U "$DB_USER" --if-exists "$DB_NAME"
  docker compose exec -T db createdb -U "$DB_USER" "$DB_NAME"
  docker compose exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner < "$work/db.dump"

  say "scan media"
  rm -rf scan_media && tar -xf "$work/scan_media.tar" -C .

  say "volumes"
  local vwork="$work/volumes"
  mkdir -p "$vwork" && tar -xf "$work/volumes.tar" -C "$vwork"
  for volume in "${VOLUMES[@]}"; do
    [ -f "$vwork/$volume.tar" ] || continue
    docker run --rm -v "$(basename "$HERE")_$volume:/to" -v "$vwork:/from" alpine \
      sh -c "rm -rf /to/* /to/..?* /to/.[!.]* 2>/dev/null; tar -xf /from/$volume.tar -C /to" >/dev/null
  done

  say "starting"
  docker compose start api worker-default worker-beat >/dev/null
  say "restored. If SECRET_KEY differs from the archive's, stored secrets will not decrypt:"
  grep -E '^SECRET_KEY=' "$work/env" | sed 's/=.*/=<in the archive>/'
}

case "${1:-}" in
  dump) dump "$@" ;;
  restore) restore "$@" ;;
  list) ls -lh "${2:-./backups}" 2>/dev/null || die "nothing in ${2:-./backups}" ;;
  *) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
esac
