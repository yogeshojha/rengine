#!/usr/bin/env bash
# Back up a reNgine instance, or restore one.
#
#   scripts/backup.sh dump [DIR]     write a dated archive to DIR (default ./backups)
#   scripts/backup.sh restore FILE   replace this instance's data with an archive
#   scripts/backup.sh list [DIR]     list the archives in DIR
#
# Archive contents:
#   db.dump          the database, pg_dump custom format
#   scan_media.tar   screenshots and stored responses
#   volumes.tar      check templates, wordlists, generated reports and report fonts
#   env              SECRET_KEY
#
# A dump run from a terminal asks for a passphrase. With one it writes rengine-*.tar.enc.
# RENGINE_BACKUP_PASSPHRASE supplies it to a dump or a restore without a prompt.
# An archive decrypts every stored secret. Store it as a credential.

set -euo pipefail
umask 077

CIPHER=(-aes-256-cbc -pbkdf2 -iter 600000 -md sha256)
PASSPHRASE="${RENGINE_BACKUP_PASSPHRASE:-}"
unset RENGINE_BACKUP_PASSPHRASE

ARG="${2:-}"
case "$ARG" in "" | /*) ;; *) ARG="$PWD/$ARG" ;; esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

DEST="${ARG:-./backups}"
DB_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || echo rengine)"
DB_NAME="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2- || echo rengine)"
VOLUMES=(vuln_templates wordlists report_fonts reports_out)
SERVICES=(api worker-default worker-scans worker-control worker-beat channels ct-stream)
PROJECT="$(docker compose config --format json 2>/dev/null \
  | sed -n 's/.*"name": *"\([^"]*\)".*/\1/p' | head -1 || true)"
PROJECT="${PROJECT:-$(basename "$HERE")}"

WORK=""
STOPPED=0
cleanup() {
  [ -n "$WORK" ] && rm -rf "$WORK"
  if [ "$STOPPED" = 1 ]; then
    docker compose start "${SERVICES[@]}" >/dev/null 2>&1 || true
    printf 'error: restore not completed. Stopped services started.\n' >&2
  fi
  return 0
}
trap cleanup EXIT

say() { printf '\033[1m%s\033[0m\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

running() { docker compose ps --format '{{.Service}}' 2>/dev/null | grep -qx "$1"; }

has_openssl() { command -v openssl >/dev/null 2>&1; }

ask_passphrase() {
  local again
  [ -n "$PASSPHRASE" ] && return 0
  [ -t 0 ] || return 0
  if ! has_openssl; then
    say "openssl not found. The archive is written unencrypted."
    return 0
  fi
  read -rsp "Passphrase to encrypt the archive, empty for none: " PASSPHRASE; printf '\n'
  [ -n "$PASSPHRASE" ] || return 0
  read -rsp "Passphrase again: " again; printf '\n'
  [ "$again" = "$PASSPHRASE" ] || die "the passphrases do not match"
}

encrypted() { [ "$(head -c 8 "$1" 2>/dev/null)" = "Salted__" ]; }

HELPER=""
need_db() {
  running db || die "the db service is not running"
  HELPER="$(docker inspect --format '{{.Config.Image}}' "$(docker compose ps -q db)")"
}

dump() {
  need_db
  ask_passphrase
  [ -z "$PASSPHRASE" ] || has_openssl || die "openssl is required to encrypt the archive"
  mkdir -p "$DEST"
  local stamp archive work
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  archive="$DEST/rengine-$stamp.tar"
  WORK="$(mktemp -d)"; work="$WORK"

  say "database"
  docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$work/db.dump"

  say "scan media"
  if [ -d scan_media ]; then
    docker run --rm -v "$HERE:/repo:ro" -v "$work:/to" "$HELPER" \
      tar -cf /to/scan_media.tar -C /repo scan_media >/dev/null
  else
    tar -cf "$work/scan_media.tar" -T /dev/null
  fi

  say "volumes"
  local vwork="$work/volumes"
  mkdir -p "$vwork"
  for volume in "${VOLUMES[@]}"; do
    docker volume inspect "${PROJECT}_$volume" >/dev/null 2>&1 \
      || die "volume ${PROJECT}_$volume does not exist. Start the stack once before a backup."
    docker run --rm -v "${PROJECT}_$volume:/from" -v "$vwork:/to" "$HELPER" \
      sh -c "tar -cf /to/$volume.tar -C /from ." >/dev/null
  done
  tar -cf "$work/volumes.tar" -C "$vwork" .

  grep -E '^SECRET_KEY=' .env > "$work/env" || true

  if [ -n "$PASSPHRASE" ]; then
    archive="$archive.enc"
    tar -cf - -C "$work" db.dump scan_media.tar volumes.tar env \
      | KEY="$PASSPHRASE" openssl enc -e "${CIPHER[@]}" -salt -pass env:KEY -out "$archive.part"
  else
    tar -cf "$archive.part" -C "$work" db.dump scan_media.tar volumes.tar env
  fi
  mv "$archive.part" "$archive"
  say "wrote $archive ($(du -h "$archive" | cut -f1))"
  say "The archive holds the instance key, SECRET_KEY."
  if [ -n "$PASSPHRASE" ]; then say "Encrypted with the passphrase."; else say "Not encrypted."; fi
}

restore() {
  local archive="$ARG"
  [ -n "$archive" ] || die "usage: scripts/backup.sh restore FILE"
  [ -f "$archive" ] || die "$archive not found"
  need_db

  local work archived current differs redis_db show
  WORK="$(mktemp -d)"; work="$WORK"
  show="tar -xOf $archive env"
  if encrypted "$archive"; then
    has_openssl || die "openssl is required to decrypt $archive"
    if [ -z "$PASSPHRASE" ]; then
      [ -t 0 ] || die "$archive is encrypted. Set RENGINE_BACKUP_PASSPHRASE or restore from a terminal."
      read -rsp "Passphrase for $archive: " PASSPHRASE; printf '\n'
    fi
    KEY="$PASSPHRASE" openssl enc -d "${CIPHER[@]}" -pass env:KEY -in "$archive" 2>/dev/null \
      | tar -xf - -C "$work" 2>/dev/null \
      || die "the passphrase does not decrypt $archive"
    show="openssl enc -d ${CIPHER[*]} -in $archive | tar -xO env"
  else
    tar -xf "$archive" -C "$work"
  fi
  archived="$(grep -E '^SECRET_KEY=' "$work/env" | cut -d= -f2- || true)"
  current="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2- || true)"
  differs="SECRET_KEY in .env differs from the archive. Copy the SECRET_KEY line from '$show' into .env and restart the stack."
  [ "$archived" = "$current" ] || say "$differs"

  printf "Type the database name %s to replace this instance's data: " "$DB_NAME"
  read -r answer
  [ "$answer" = "$DB_NAME" ] || die "not confirmed"

  say "stopping the services that use the database"
  STOPPED=1
  docker compose stop "${SERVICES[@]}" >/dev/null

  say "database"
  docker compose exec -T db dropdb -U "$DB_USER" --if-exists --force "$DB_NAME"
  docker compose exec -T db createdb -U "$DB_USER" "$DB_NAME"
  docker compose exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner < "$work/db.dump"

  say "cache"
  redis_db="$(grep -E '^REDIS_DB=' .env | cut -d= -f2- || true)"
  [[ "$redis_db" =~ ^[0-9]+$ ]] || redis_db=0
  docker compose exec -T redis sh -c \
    "redis-cli \${REDIS_PASSWORD:+-a \"\$REDIS_PASSWORD\"} --no-auth-warning -n $redis_db INCR rev:global" >/dev/null \
    || say "cached aggregates not cleared"

  say "scan media"
  docker run --rm -v "$HERE:/repo" -v "$work:/from:ro" "$HELPER" \
    sh -c 'rm -rf /repo/scan_media && tar -xf /from/scan_media.tar -C /repo' >/dev/null

  say "volumes"
  local vwork="$work/volumes"
  mkdir -p "$vwork" && tar -xf "$work/volumes.tar" -C "$vwork"
  for volume in "${VOLUMES[@]}"; do
    [ -f "$vwork/$volume.tar" ] || continue
    docker run --rm -v "${PROJECT}_$volume:/to" -v "$vwork:/from" "$HELPER" \
      sh -c "rm -rf /to/* /to/..?* /to/.[!.]* 2>/dev/null; tar -xf /from/$volume.tar -C /to" >/dev/null
  done
  if docker compose config --services 2>/dev/null | grep -qx volume-init; then
    docker compose run --rm --no-deps volume-init >/dev/null 2>&1 || say "data directory owners not checked"
  fi

  say "starting"
  docker compose start "${SERVICES[@]}" >/dev/null
  STOPPED=0
  say "restored"
  [ "$archived" = "$current" ] || say "$differs"
}

case "${1:-}" in
  dump) dump ;;
  restore) restore ;;
  list) ls -lh "${ARG:-./backups}" 2>/dev/null || die "nothing in ${ARG:-./backups}" ;;
  *) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
esac
