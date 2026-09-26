#!/usr/bin/env bash
# Bump the packages in api/uv.lock and worker/uv.lock that have a published advisory.
#
# Dependabot cannot do this: both projects depend on `rengine-shared @ file:///app/shared`
# (and tools), a path that exists only inside the images. Here /app/shared and /app/tools
# are pointed at the checkout, so uv resolves the locks exactly as the image builds do.
# Prints a markdown summary on stdout; exits 0 whether or not anything changed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [ ! -e /app/shared ] || [ ! -e /app/tools ]; then
  ${SUDO:-} mkdir -p /app
  ${SUDO:-} ln -sfn "$ROOT/shared" /app/shared
  ${SUDO:-} ln -sfn "$ROOT/tools" /app/tools
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

audit() { # project, output json
  local project="$1" out="$2" req="$tmp/$1.txt" status=0
  uv export --project "$ROOT/$project" --frozen --no-hashes --no-emit-project \
    --no-emit-local --all-groups --format requirements-txt -q > "$req"
  # pip-audit exits 1 when it finds advisories; anything else, or no report, is a failed audit
  # and must not read as "nothing found"
  uv tool run --quiet pip-audit --disable-pip --no-deps -r "$req" -f json -o "$out" \
    --progress-spinner off 2>/dev/null || status=$?
  if [ "$status" -gt 1 ] || [ ! -s "$out" ]; then
    echo "pip-audit failed for $project (exit $status)" >&2
    exit 1
  fi
}

fixable() { # json -> names of packages with a released fix
  python3 - "$1" <<'PY'
import json, sys
for dep in json.load(open(sys.argv[1])).get("dependencies", []):
    if any(v.get("fix_versions") for v in dep.get("vulns", [])):
        print(dep["name"])
PY
}

for project in api worker; do
  audit "$project" "$tmp/$project.json"
  mapfile -t vulnerable < <(fixable "$tmp/$project.json")
  if [ ${#vulnerable[@]} -eq 0 ]; then
    echo "- \`$project\`: no fixable advisories"
    continue
  fi
  args=()
  for name in "${vulnerable[@]}"; do args+=(--upgrade-package "$name"); done
  cp "$ROOT/$project/uv.lock" "$tmp/$project.before"
  uv lock --project "$ROOT/$project" -q "${args[@]}"
  python3 - "$tmp/$project.before" "$ROOT/$project/uv.lock" "$project" <<'PY'
import sys, tomllib
old = {p["name"]: p["version"] for p in tomllib.load(open(sys.argv[1], "rb"))["package"] if "version" in p}
new = {p["name"]: p["version"] for p in tomllib.load(open(sys.argv[2], "rb"))["package"] if "version" in p}
changed = [f"{n} {old[n]} → {new[n]}" for n in sorted(new) if n in old and old[n] != new[n]]
print(f"- `{sys.argv[3]}`: " + (", ".join(changed) if changed else "no newer version resolves"))
PY
  # a package another dependency caps (starlette under fastapi, say) stays behind: name it
  audit "$project" "$tmp/$project.after.json"
  mapfile -t remaining < <(fixable "$tmp/$project.after.json")
  if [ ${#remaining[@]} -gt 0 ]; then
    echo "  - still vulnerable, held back by a dependent's constraint: ${remaining[*]}"
  fi
done
