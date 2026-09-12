#!/bin/sh
# certspotter -script: spool the certspotter fields for the supervisor
d="${CT_SPOOL_DIR:-/app/ct-state/spool}"
mkdir -p "$d"
f="$d/$(date +%s%N)-$$"
{
  for k in EVENT SUMMARY WATCH_ITEM LOG_URI ENTRY_INDEX CERT_SHA256 TBS_SHA256 \
           JSON_FILENAME TEXT_FILENAME NOT_BEFORE_RFC3339 NOT_AFTER_RFC3339 \
           ISSUER_DN SUBJECT_DN SERIAL; do
    eval "v=\${$k}"
    [ -n "$v" ] && printf '%s=%s\n' "$k" "$v"
  done
  :
} > "$f.tmp" && mv "$f.tmp" "$f.env"
