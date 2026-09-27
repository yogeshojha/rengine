#!/usr/bin/env bash
# install reNgine: docker compose stack behind caddy, guided or via --help flags
set -euo pipefail

REPO="yogeshojha/rengine"
IMAGE_PREFIX="yogeshojha/rengine"
DOCKER_SUBNET="172.29.0.0/24"
CADDY_ADDR="172.29.0.253"

# ---------- output ----------

if [ -t 1 ]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
  BOLD=""; DIM=""; RED=""; RESET=""
fi

say() { printf '%s\n' "$*"; }
step() { printf '\n%s%s%s\n' "$BOLD" "$*" "$RESET"; }
die() { printf '%serror:%s %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

WORK=""
cleanup() { [ -t 1 ] && printf '\033[?25h'; [ -n "$WORK" ] && rm -rf "$WORK"; return 0; }
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

# ---------- prompts ----------

SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# a piped script cannot take /dev/tty: bash would read the script text from it
INTERACTIVE=0
if [ -t 0 ]; then
  INTERACTIVE=1
elif [ -n "$SCRIPT_DIR" ] && [ -e /dev/tty ] && (exec </dev/tty) 2>/dev/null; then
  exec </dev/tty
  INTERACTIVE=1
fi

CHOICE=0
choose() {
  local prompt="$1"; shift
  local opts=("$@")
  local n=${#opts[@]} idx=0 key rest i
  printf '\n%s%s%s\n' "$BOLD" "$prompt" "$RESET"
  printf '\033[?25l'
  while :; do
    i=0
    while [ "$i" -lt "$n" ]; do
      if [ "$i" -eq "$idx" ]; then
        printf '  %s> %s%s\033[K\n' "$BOLD" "${opts[$i]}" "$RESET"
      else
        printf '    %s%s%s\033[K\n' "$DIM" "${opts[$i]}" "$RESET"
      fi
      i=$((i + 1))
    done
    IFS= read -rsn1 key || key=""
    if [ "$key" = $'\x1b' ]; then
      IFS= read -rsn2 -t 1 rest || rest=""
      key="$key$rest"
    fi
    case "$key" in
      $'\x1b[A' | k) [ "$idx" -gt 0 ] && idx=$((idx - 1)) || true ;;
      $'\x1b[B' | j) [ "$idx" -lt $((n - 1)) ] && idx=$((idx + 1)) || true ;;
      "") break ;;
    esac
    printf '\033[%dA' "$n"
  done
  printf '\033[?25h'
  CHOICE=$idx
}

ANSWER=""
ask() {
  local prompt="$1" def="${2:-}"
  if [ "$INTERACTIVE" -eq 0 ]; then ANSWER="$def"; return 0; fi
  if [ -n "$def" ]; then
    read -rp "$BOLD$prompt$RESET [$def] " ANSWER || ANSWER=""
    ANSWER="${ANSWER:-$def}"
  else
    read -rp "$BOLD$prompt$RESET " ANSWER || ANSWER=""
  fi
}

ask_secret() {
  local prompt="$1"
  ANSWER=""
  [ "$INTERACTIVE" -eq 0 ] && return 0
  read -rsp "$BOLD$prompt$RESET " ANSWER || ANSWER=""
  printf '\n'
}

confirm() {
  local prompt="$1" def="${2:-n}" hint ans
  if [ "$INTERACTIVE" -eq 0 ]; then [ "$def" = y ]; return; fi
  if [ "$def" = y ]; then hint="Y/n"; else hint="y/N"; fi
  read -rp "$BOLD$prompt$RESET [$hint] " ans || ans=""
  ans="${ans:-$def}"
  case "$ans" in y | Y | yes | Yes) return 0 ;; *) return 1 ;; esac
}

# ---------- helpers ----------

rand_hex() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$1"
  else
    od -vN "$1" -An -tx1 /dev/urandom | tr -d ' \n'
  fi
}

valid_port() { [[ "$1" =~ ^[0-9]+$ ]] && [ "$1" -ge 1 ] && [ "$1" -le 65535 ]; }

port_free() {
  command -v ss >/dev/null 2>&1 || return 0
  ! ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]$1\$"
}

env_get() { grep -E "^$1=" "$2" 2>/dev/null | head -1 | cut -d= -f2-; }

# ---------- flags ----------

MODE=""
RENGINE_HOST=""
SERVER_IP=""
UI_PORT=""
API_PORT=""
ADMIN_USERNAME=""
ADMIN_EMAIL=""
ADMIN_PASSWORD=""
ACME_EMAIL=""
RENGINE_HOME=""
GIT_TAG=""
BUILD=0
NO_START=0
FORCE=0
NO_API=0
API_FLAGGED=0

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Run without flags for the guided setup.

Reachability, one of
  --domain <name>       public domain, HTTPS certificate from Let's Encrypt
  --ip [address]        server address, self-signed certificate
  --local               this machine only, no TLS

Options
  --ui-port <port>      published UI port, fixed at 443 with --domain
  --api-port <port>     publish the API on its own port
  --no-api-port         stop publishing the API on its own port
  --admin-user <name>   first administrator, default rengine
  --admin-email <mail>
  --admin-password <pw> default is a generated one, shown once
  --acme-email <mail>   Let's Encrypt account email
  --dir <path>          install directory
  --tag <tag>           release to install, default the latest
  --build               build images from this checkout instead of pulling
  --no-start            write the configuration and stop
  --force               skip the memory, disk and port checks
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) MODE=domain; RENGINE_HOST="${2:?--domain needs a name}"; shift ;;
    --ip)
      MODE=ip
      if [ $# -gt 1 ] && [[ "${2}" != --* ]]; then SERVER_IP="$2"; shift; fi ;;
    --local) MODE=local ;;
    --ui-port) UI_PORT="${2:?}"; shift ;;
    --api-port) API_PORT="${2:?}"; API_FLAGGED=1; shift ;;
    --no-api-port) NO_API=1 ;;
    --admin-user) ADMIN_USERNAME="${2:?}"; shift ;;
    --admin-email) ADMIN_EMAIL="${2:?}"; shift ;;
    --admin-password) ADMIN_PASSWORD="${2:?}"; shift ;;
    --acme-email) ACME_EMAIL="${2:?}"; shift ;;
    --dir) RENGINE_HOME="${2:?}"; shift ;;
    --tag) GIT_TAG="${2:?}"; shift ;;
    --build) BUILD=1 ;;
    --no-start) NO_START=1 ;;
    --force) FORCE=1 ;;
    -h | --help) usage; exit 0 ;;
    *) die "unknown option: $1. See --help" ;;
  esac
  shift
done

# ---------- environment ----------

[ "$(uname -s)" = "Linux" ] || die "Linux is required. On another OS, run the dev compose from a checkout."
case "$(uname -m)" in
  x86_64) ;;
  aarch64) [ "$BUILD" -eq 1 ] || die "arm64 worker images are not published. Install from a checkout with --build." ;;
  *) die "unsupported architecture: $(uname -m)" ;;
esac

CHECKOUT=0
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/docker-compose.prod.yml" ]; then
  CHECKOUT=1
fi

[ "$BUILD" -eq 1 ] && [ "$CHECKOUT" -eq 0 ] && die "--build needs a repository checkout"

if [ -z "$RENGINE_HOME" ]; then
  if [ "$(id -u)" -eq 0 ]; then RENGINE_HOME="/opt/rengine"; else RENGINE_HOME="$HOME/rengine"; fi
fi
[ "$CHECKOUT" -eq 1 ] && [ "$RENGINE_HOME" = "$SCRIPT_DIR" ] && die "the install directory cannot be the checkout. Pass another --dir."

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    say "Docker not found."
    local sudo_cmd=""
    if [ "$(id -u)" -ne 0 ]; then
      command -v sudo >/dev/null 2>&1 || die "installing Docker needs root. Install Docker, then run this script again."
      sudo_cmd="sudo"
    fi
    confirm "Install Docker from get.docker.com now" y || die "install Docker, then run this script again"
    curl -fsSL https://get.docker.com | $sudo_cmd sh
    $sudo_cmd systemctl enable --now docker 2>/dev/null || true
  fi
  docker info >/dev/null 2>&1 || die "docker is not usable from this account. Run as root or add the user to the docker group and sign in again."
  docker compose version >/dev/null 2>&1 || die "the docker compose plugin is missing. Install docker-compose-plugin, then run this script again."
}

MEM_GB=0
CPUS=1
TIER=""
check_resources() {
  # MemTotal rounded to the nearest GB
  MEM_GB=$((($(awk '/MemTotal/ {print $2}' /proc/meminfo) + 524288) / 1048576))
  CPUS="$(nproc 2>/dev/null || echo 1)"
  if [ "$MEM_GB" -lt 4 ] && [ "$FORCE" -eq 0 ]; then
    die "$MEM_GB GB memory found. 4 GB is the minimum, 8 GB is recommended. --force overrides."
  fi
  local parent free_mb
  parent="$(dirname "$RENGINE_HOME")"
  [ -d "$parent" ] || parent="/"
  free_mb="$(df -Pm "$parent" 2>/dev/null | awk 'NR==2 {print $4}')"
  if [ -n "$free_mb" ] && [ "$free_mb" -lt 10240 ] && [ "$FORCE" -eq 0 ]; then
    die "$((free_mb / 1024)) GB disk free on $parent. 10 GB is the minimum, 25 GB is recommended. --force overrides."
  fi
  if [ "$MEM_GB" -lt 8 ]; then TIER=small
  elif [ "$MEM_GB" -lt 16 ]; then TIER=medium
  else TIER=large; fi
}

# per-tier sizing: postgres, redis and worker slots follow the machine
PG_SHARED_BUFFERS=""; PG_EFFECTIVE_CACHE=""; PG_WORK_MEM=""; PG_MAINT_MEM=""; PG_SHM=""
REDIS_MAXMEMORY=""; SCAN_SLOTS=""; CONTROL_SLOTS=""; DEFAULT_SLOTS=""; API_WORKERS=""
apply_tier() {
  case "$TIER" in
    small)
      PG_SHARED_BUFFERS=512MB; PG_EFFECTIVE_CACHE=2GB; PG_WORK_MEM=16MB; PG_MAINT_MEM=128MB; PG_SHM=512mb
      REDIS_MAXMEMORY=512mb; SCAN_SLOTS=8; CONTROL_SLOTS=4; DEFAULT_SLOTS=2; API_WORKERS=2 ;;
    medium)
      PG_SHARED_BUFFERS=1GB; PG_EFFECTIVE_CACHE=4GB; PG_WORK_MEM=32MB; PG_MAINT_MEM=256MB; PG_SHM=1gb
      REDIS_MAXMEMORY=1gb; SCAN_SLOTS=12; CONTROL_SLOTS=8; DEFAULT_SLOTS=4; API_WORKERS=4 ;;
    *)
      PG_SHARED_BUFFERS=2GB; PG_EFFECTIVE_CACHE=6GB; PG_WORK_MEM=32MB; PG_MAINT_MEM=512MB; PG_SHM=1gb
      REDIS_MAXMEMORY=1gb; SCAN_SLOTS=16; CONTROL_SLOTS=8; DEFAULT_SLOTS=4; API_WORKERS=4 ;;
  esac
}

IMAGE_TAG=""
resolve_tag() {
  if [ -n "$GIT_TAG" ]; then IMAGE_TAG="${GIT_TAG#v}"; return 0; fi
  if [ "$CHECKOUT" -eq 1 ]; then
    IMAGE_TAG="$(tr -d ' \n' <"$SCRIPT_DIR/VERSION")"
    GIT_TAG="v$IMAGE_TAG"
    return 0
  fi
  GIT_TAG="$(curl -fsSLm 15 "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
    | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p')"
  [ -n "$GIT_TAG" ] || die "GitHub did not answer with the latest release. Pass --tag."
  IMAGE_TAG="${GIT_TAG#v}"
}

SRC_DIR=""
fetch_source() {
  if [ "$CHECKOUT" -eq 1 ]; then SRC_DIR="$SCRIPT_DIR"; return 0; fi
  step "Fetching reNgine $GIT_TAG"
  WORK="$(mktemp -d)"
  curl -fsSL "https://github.com/$REPO/archive/refs/tags/$GIT_TAG.tar.gz" | tar -xz -C "$WORK" \
    || die "could not download $GIT_TAG from GitHub"
  SRC_DIR="$(find "$WORK" -maxdepth 1 -mindepth 1 -type d | head -1)"
  [ -f "$SRC_DIR/docker-compose.prod.yml" ] || die "the $GIT_TAG archive has no docker-compose.prod.yml"
}

# ---------- existing install ----------

RECONFIGURE=0
KEEP_SETTINGS=0
SECRET_KEY=""; POSTGRES_PASSWORD=""; REDIS_PASSWORD=""; FLOWER_PASSWORD=""
load_existing() {
  local env_file="$RENGINE_HOME/.env"
  [ -f "$env_file" ] || return 0
  grep -q '^COMPOSE_FILE=docker-compose.prod.yml' "$env_file" \
    || die "$RENGINE_HOME holds a .env this installer did not write. Pass an empty directory with --dir."
  say ""
  say "An install exists in $RENGINE_HOME."
  if [ "$INTERACTIVE" -eq 1 ]; then
    choose "How to continue" "Keep the settings and redeploy" "Reconfigure"
    [ "$CHOICE" -eq 0 ] && KEEP_SETTINGS=1 || RECONFIGURE=1
  elif [ -n "$MODE" ]; then
    # a reachability flag on an existing install is a reconfigure
    RECONFIGURE=1
  else
    KEEP_SETTINGS=1
  fi
  SECRET_KEY="$(env_get SECRET_KEY "$env_file")"
  POSTGRES_PASSWORD="$(env_get POSTGRES_PASSWORD "$env_file")"
  REDIS_PASSWORD="$(env_get REDIS_PASSWORD "$env_file")"
  FLOWER_PASSWORD="$(env_get FLOWER_PASSWORD "$env_file")"
  # a flag wins over the stored value
  [ -n "$ADMIN_USERNAME" ] || ADMIN_USERNAME="$(env_get ADMIN_USERNAME "$env_file")"
  [ -n "$ADMIN_EMAIL" ] || ADMIN_EMAIL="$(env_get ADMIN_EMAIL "$env_file")"
  [ -n "$ADMIN_PASSWORD" ] || ADMIN_PASSWORD="$(env_get ADMIN_PASSWORD "$env_file")"
  [ -n "$ACME_EMAIL" ] || ACME_EMAIL="$(env_get ACME_EMAIL "$env_file")"
}

# reconfigure rewrites the reachability keys alone; tag, sizing and edits stay
update_env() {
  sed -i \
    -e "s|^PUBLIC_ORIGIN=.*|PUBLIC_ORIGIN=$PUBLIC_ORIGIN|" \
    -e "s|^RENGINE_HOST=.*|RENGINE_HOST=$RENGINE_HOST|" \
    -e "s|^ACME_EMAIL=.*|ACME_EMAIL=$ACME_EMAIL|" \
    -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=[\"$PUBLIC_ORIGIN\"]|" \
    -e "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=$ADMIN_EMAIL|" \
    -e "s|^ADMIN_USERNAME=.*|ADMIN_USERNAME=$ADMIN_USERNAME|" \
    -e "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$ADMIN_PASSWORD|" \
    "$RENGINE_HOME/.env"
}

# ---------- wizard ----------

PUBLIC_ORIGIN=""
GENERATED_PASSWORD=0

ask_mode() {
  [ -n "$MODE" ] && return 0
  [ "$INTERACTIVE" -eq 1 ] || die "no terminal for the guided setup. Download install.sh and run it, or pass --domain, --ip or --local."
  choose "Where is this instance reached?" \
    "Public domain, HTTPS certificate from Let's Encrypt" \
    "Server address, self-signed certificate" \
    "This machine only, no TLS"
  case "$CHOICE" in
    0) MODE=domain ;;
    1) MODE=ip ;;
    2) MODE=local ;;
  esac
}

detect_ip() {
  ip route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9a-f.:]*\).*/\1/p' | head -1
}

ask_reachability() {
  case "$MODE" in
    domain)
      RENGINE_HOST="$(printf '%s' "$RENGINE_HOST" | tr '[:upper:]' '[:lower:]')"
      while ! [[ "$RENGINE_HOST" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}$ ]]; do
        [ -n "$RENGINE_HOST" ] && say "Not a domain name: $RENGINE_HOST"
        [ "$INTERACTIVE" -eq 1 ] || die "not a domain name: $RENGINE_HOST"
        ask "Domain"
        RENGINE_HOST="$(printf '%s' "$ANSWER" | tr '[:upper:]' '[:lower:]')"
      done
      UI_PORT=443
      PUBLIC_ORIGIN="https://$RENGINE_HOST"
      say "DNS for $RENGINE_HOST must point at this server. Ports 443 and 80 are published."
      ;;
    ip)
      if [ -z "$SERVER_IP" ]; then
        ask "Server address" "$(detect_ip)"
        SERVER_IP="$ANSWER"
      fi
      [ -n "$SERVER_IP" ] || die "no server address"
      if [ -z "$UI_PORT" ]; then
        ask "UI port" "443"
        UI_PORT="$ANSWER"
      fi
      valid_port "$UI_PORT" || die "not a port: $UI_PORT"
      if [ "$UI_PORT" = "443" ]; then PUBLIC_ORIGIN="https://$SERVER_IP"; else PUBLIC_ORIGIN="https://$SERVER_IP:$UI_PORT"; fi
      ;;
    local)
      if [ -z "$UI_PORT" ]; then
        ask "UI port" "8080"
        UI_PORT="$ANSWER"
      fi
      valid_port "$UI_PORT" || die "not a port: $UI_PORT"
      if [ "$UI_PORT" = "80" ]; then PUBLIC_ORIGIN="http://localhost"; else PUBLIC_ORIGIN="http://localhost:$UI_PORT"; fi
      say "Published on 127.0.0.1 only."
      say "Home uplinks behind CGNAT drop scan connections. A VPS is the reliable place to scan from."
      ;;
  esac

  # a reconfigured instance already holds its own ports
  [ "$RECONFIGURE" -eq 1 ] && return 0
  [ "$FORCE" -eq 1 ] && return 0
  port_free "$UI_PORT" || die "port $UI_PORT is in use"
  if [ "$MODE" = "domain" ]; then
    port_free 80 || die "port 80 is in use and Let's Encrypt needs it"
  fi
  if [ "$MODE" = "ip" ] && [ "$UI_PORT" = "443" ]; then
    port_free 80 || die "port 80 is in use. Pass a UI port other than 443 to skip the redirect listener."
  fi
}

ask_api() {
  if [ "$NO_API" -eq 1 ]; then
    API_PORT=""
    return 0
  fi
  if [ -n "$API_PORT" ]; then
    valid_port "$API_PORT" || die "not a port: $API_PORT"
    if [ "$RECONFIGURE" -eq 1 ] && [ "$API_FLAGGED" -eq 0 ] && [ "$INTERACTIVE" -eq 1 ]; then
      confirm "Keep the API published on port $API_PORT" y || API_PORT=""
    fi
    return 0
  fi
  [ "$INTERACTIVE" -eq 1 ] || return 0
  say ""
  say "The interface, agents and connectors reach the API at $PUBLIC_ORIGIN/api."
  if confirm "Publish the API on its own port as well" n; then
    ask "API port" "8000"
    API_PORT="$ANSWER"
    valid_port "$API_PORT" || die "not a port: $API_PORT"
    if [ "$RECONFIGURE" -eq 0 ] && [ "$FORCE" -eq 0 ]; then
      port_free "$API_PORT" || die "port $API_PORT is in use"
    fi
  fi
}

ask_admin() {
  if [ -z "$ADMIN_USERNAME" ]; then
    ask "Admin username" "rengine"
    ADMIN_USERNAME="$ANSWER"
  fi
  if [ -z "$ADMIN_EMAIL" ]; then
    local def="admin@rengine.local"
    [ "$MODE" = "domain" ] && def="admin@$RENGINE_HOST"
    ask "Admin email" "$def"
    ADMIN_EMAIL="$ANSWER"
  fi
  if [ -z "$ADMIN_PASSWORD" ]; then
    ask_secret "Admin password, empty generates one"
    ADMIN_PASSWORD="$ANSWER"
    if [ -z "$ADMIN_PASSWORD" ]; then
      ADMIN_PASSWORD="$(rand_hex 9)"
      GENERATED_PASSWORD=1
    fi
  fi
  [[ "$ADMIN_PASSWORD" =~ ^[A-Za-z0-9@._%+=:,^~/-]+$ ]] \
    || die "the admin password takes letters, digits and @._%+=:,^~/- here. Set a simple one and change it in Settings."
}

# ---------- files ----------

write_caddyfile() {
  local email_line=""
  [ -n "$ACME_EMAIL" ] && email_line="	email $ACME_EMAIL"
  case "$MODE" in
    domain)
      cat >"$RENGINE_HOME/Caddyfile" <<EOF
{
	admin off
$email_line
}

$RENGINE_HOST {
	encode zstd gzip

	handle /api/* {
		reverse_proxy api:8000 {
			flush_interval -1
		}
	}

	handle {
		reverse_proxy frontend:3000
	}
}
EOF
      ;;
    ip)
      cat >"$RENGINE_HOME/Caddyfile" <<EOF
{
	admin off
	default_sni $SERVER_IP
}

https://$SERVER_IP {
	tls internal
	encode zstd gzip

	handle /api/* {
		reverse_proxy api:8000 {
			flush_interval -1
		}
	}

	handle {
		reverse_proxy frontend:3000
	}
}

http://:80 {
	redir https://{host}{uri}
}
EOF
      ;;
    local)
      cat >"$RENGINE_HOME/Caddyfile" <<'EOF'
{
	admin off
	auto_https off
}

http://:80 {
	encode zstd gzip

	handle /api/* {
		reverse_proxy api:8000 {
			flush_interval -1
		}
	}

	handle {
		reverse_proxy frontend:3000
	}
}
EOF
      ;;
  esac
}

write_ports() {
  # local binds loopback, the other modes bind every interface, v6 included
  {
    echo "# written by install.sh; every published port is decided here"
    echo "services:"
    echo "  caddy:"
    echo "    ports:"
    case "$MODE" in
      domain)
        echo "      - \"443:443\""
        echo "      - \"80:80\""
        ;;
      ip)
        echo "      - \"$UI_PORT:443\""
        [ "$UI_PORT" = "443" ] && echo "      - \"80:80\""
        ;;
      local)
        echo "      - \"127.0.0.1:$UI_PORT:80\""
        ;;
    esac
    if [ -n "$API_PORT" ]; then
      echo "  api:"
      echo "    ports:"
      if [ "$MODE" = "local" ]; then
        echo "      - \"127.0.0.1:$API_PORT:8000\""
      else
        echo "      - \"$API_PORT:8000\""
      fi
    fi
  } >"$RENGINE_HOME/ports.yml"
}

write_env() {
  local cors="[\"$PUBLIC_ORIGIN\"]"
  local src=""
  [ "$BUILD" -eq 1 ] && src="$SCRIPT_DIR"
  cat >"$RENGINE_HOME/.env.tmp" <<EOF
# written by install.sh $(date -u +%Y-%m-%dT%H:%M:%SZ)

COMPOSE_PROJECT_NAME=rengine3
COMPOSE_FILE=docker-compose.prod.yml:ports.yml
RENGINE_IMAGE=$IMAGE_PREFIX
RENGINE_TAG=$IMAGE_TAG
RENGINE_SRC=$src
PUBLIC_ORIGIN=$PUBLIC_ORIGIN
RENGINE_HOST=$RENGINE_HOST
ACME_EMAIL=$ACME_EMAIL
DOCKER_SUBNET=$DOCKER_SUBNET
CADDY_ADDR=$CADDY_ADDR

# ---------- application ----------
DEBUG=false
LOG_LEVEL=INFO
SQL_ECHO=false

# ---------- database ----------
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=rengine
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=rengine

POSTGRES_SHARED_BUFFERS=$PG_SHARED_BUFFERS
POSTGRES_EFFECTIVE_CACHE_SIZE=$PG_EFFECTIVE_CACHE
POSTGRES_WORK_MEM=$PG_WORK_MEM
POSTGRES_MAINTENANCE_WORK_MEM=$PG_MAINT_MEM
POSTGRES_MAX_CONNECTIONS=250
POSTGRES_LOG_MIN_DURATION=2000
POSTGRES_SHM_SIZE=$PG_SHM

# ---------- connection pools, per api process ----------
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=10
DB_POOL_RECYCLE=1800
DB_IDLE_TX_TIMEOUT=120

WORKER_DB_POOL_SIZE=2
WORKER_DB_MAX_OVERFLOW=3
WORKER_DB_POOL_TIMEOUT=30

# ---------- redis ----------
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_MAXMEMORY=$REDIS_MAXMEMORY

# ---------- celery ----------
CELERY_SCAN_CONCURRENCY=$SCAN_SLOTS
CELERY_CONTROL_CONCURRENCY=$CONTROL_SLOTS
CELERY_DEFAULT_CONCURRENCY=$DEFAULT_SLOTS
TASK_SOFT_TIME_LIMIT=21600
TASK_HARD_TIME_LIMIT=28800

# ---------- api ----------
SECRET_KEY=$SECRET_KEY
CORS_ORIGINS=$cors
API_RELOAD=false
API_WORKERS=$API_WORKERS
GLOBAL_RATE_LIMIT_PER_MINUTE=600
TRUSTED_PROXIES=$CADDY_ADDR

# ---------- first administrator ----------
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD

# ---------- flower, debug profile only ----------
FLOWER_USER=admin
FLOWER_PASSWORD=$FLOWER_PASSWORD

# ---------- outbound calls that are not scan traffic ----------
EGRESS_PROXY_URL=
EGRESS_TIMEOUT=30
EOF
  chmod 600 "$RENGINE_HOME/.env.tmp"
  mv "$RENGINE_HOME/.env.tmp" "$RENGINE_HOME/.env"
}

write_files() {
  step "Writing $RENGINE_HOME"
  mkdir -p "$RENGINE_HOME/scripts" "$RENGINE_HOME/scan_media" "$RENGINE_HOME/backups" "$RENGINE_HOME/bin"
  chmod 700 "$RENGINE_HOME/backups"
  cp "$SRC_DIR/docker-compose.prod.yml" "$RENGINE_HOME/"
  install -m 755 "$SRC_DIR/scripts/backup.sh" "$RENGINE_HOME/scripts/backup.sh"
  install -m 755 "$SRC_DIR/deploy/rengine" "$RENGINE_HOME/bin/rengine"
  [ -z "$SECRET_KEY" ] && SECRET_KEY="$(rand_hex 32)"
  [ -z "$POSTGRES_PASSWORD" ] && POSTGRES_PASSWORD="$(rand_hex 16)"
  [ -z "$REDIS_PASSWORD" ] && REDIS_PASSWORD="$(rand_hex 16)"
  [ -z "$FLOWER_PASSWORD" ] && FLOWER_PASSWORD="$(rand_hex 12)"
  write_env
  write_caddyfile
  write_ports
  link_cli
}

link_cli() {
  local cli="$RENGINE_HOME/bin/rengine"
  if [ -w /usr/local/bin ] || [ "$(id -u)" -eq 0 ]; then
    ln -sf "$cli" /usr/local/bin/rengine
  elif [ -d "$HOME/.local/bin" ]; then
    ln -sf "$cli" "$HOME/.local/bin/rengine"
  else
    say "Add to PATH for the rengine command: $cli"
  fi
}

refresh_keep() {
  if [ "$CHECKOUT" -eq 1 ]; then
    resolve_tag
    SRC_DIR="$SCRIPT_DIR"
  elif [ -n "$GIT_TAG" ]; then
    IMAGE_TAG="${GIT_TAG#v}"
    fetch_source
  else
    return 0
  fi
  mkdir -p "$RENGINE_HOME/scripts" "$RENGINE_HOME/bin"
  cp "$SRC_DIR/docker-compose.prod.yml" "$RENGINE_HOME/"
  install -m 755 "$SRC_DIR/scripts/backup.sh" "$RENGINE_HOME/scripts/backup.sh"
  install -m 755 "$SRC_DIR/deploy/rengine" "$RENGINE_HOME/bin/rengine"
  sed -i "s|^RENGINE_TAG=.*|RENGINE_TAG=$IMAGE_TAG|" "$RENGINE_HOME/.env"
  [ "$BUILD" -eq 1 ] && sed -i "s|^RENGINE_SRC=.*|RENGINE_SRC=$SCRIPT_DIR|" "$RENGINE_HOME/.env"
  return 0
}

# ---------- deploy ----------

check_collisions() {
  docker compose ls -q 2>/dev/null | grep -qx rengine3 \
    && die "a docker compose project named rengine3 is already running. Stop it, then run this script again."
  docker volume inspect rengine3_postgres_data >/dev/null 2>&1 \
    && die "a rengine3_postgres_data volume exists from an earlier install. Restore it with rengine restore, or remove it: docker volume rm rengine3_postgres_data"
  return 0
}

deploy() {
  cd "$RENGINE_HOME"
  if [ "$BUILD" -eq 1 ]; then
    step "Building images"
    docker compose build || die "the image build failed. The output above names the step."
  else
    step "Pulling images"
    docker compose pull || die "the image pull failed. Check the network and the release tag: $(env_get RENGINE_TAG .env)"
  fi
  step "Starting"
  docker compose up -d --remove-orphans || die "the stack did not start. Check the output above and the logs: rengine logs"
}

wait_healthy() {
  local url="$PUBLIC_ORIGIN/api/v1/health/health" tries=0
  local -a extra=()
  # probe this machine's caddy, wherever the name points
  [ "$MODE" != "local" ] && extra=(--connect-to "::127.0.0.1:")
  printf 'Waiting for the API'
  while [ "$tries" -lt 90 ]; do
    if curl -ksfm 5 "${extra[@]}" "$url" >/dev/null 2>&1; then
      printf '\n'
      return 0
    fi
    printf '.'
    sleep 2
    tries=$((tries + 1))
  done
  printf '\n'
  say "The API did not respond within three minutes. Check the logs: rengine logs api"
  [ "$MODE" = "domain" ] && say "For a domain, DNS must point here and port 80 must be reachable from the internet."
  if [ "$GENERATED_PASSWORD" -eq 1 ]; then
    say "Sign in at $PUBLIC_ORIGIN once the API answers. Username $ADMIN_USERNAME, password $ADMIN_PASSWORD. Shown once."
  fi
  exit 1
}

summary() {
  say ""
  say "${BOLD}reNgine is running.${RESET}"
  say ""
  say "  URL       $PUBLIC_ORIGIN"
  if [ "$KEEP_SETTINGS" -eq 1 ] || [ "$RECONFIGURE" -eq 1 ]; then
    say "  Sign in   admin credentials unchanged"
  else
    say "  Username  $ADMIN_USERNAME"
    if [ "$GENERATED_PASSWORD" -eq 1 ]; then
      say "  Password  $ADMIN_PASSWORD"
      say "            Shown once. Change it in Settings."
    fi
  fi
  [ "$MODE" = "ip" ] && say "  The certificate is self-signed. The browser shows a warning for it."
  [ -n "$API_PORT" ] && say "  API       port $API_PORT"
  say ""
  say "  Manage    rengine status, rengine logs, rengine update, rengine backup"
  say "  Files     $RENGINE_HOME"
  say ""
  say "Setup continues in the browser after the first sign-in."
}

# ---------- main ----------

main() {
  say ""
  say "${BOLD}reNgine installer${RESET}"

  ensure_docker
  check_resources
  apply_tier
  load_existing
  if [ "$KEEP_SETTINGS" -eq 0 ] && [ "$RECONFIGURE" -eq 0 ]; then
    check_collisions
  fi

  if [ "$KEEP_SETTINGS" -eq 1 ]; then
    PUBLIC_ORIGIN="$(env_get PUBLIC_ORIGIN "$RENGINE_HOME/.env")"
    RENGINE_HOST="$(env_get RENGINE_HOST "$RENGINE_HOME/.env")"
    API_PORT="$(sed -n 's/.*:\([0-9]*\):8000".*/\1/p' "$RENGINE_HOME/ports.yml" 2>/dev/null | head -1)"
    MODE=local
    [ -n "$RENGINE_HOST" ] && MODE=domain
    case "$PUBLIC_ORIGIN" in https://*) [ "$MODE" = "domain" ] || MODE=ip ;; esac
    refresh_keep
    [ "$NO_START" -eq 1 ] && { say "Configuration kept."; return 0; }
    deploy
    wait_healthy
    summary
    return 0
  fi

  if [ "$RECONFIGURE" -eq 1 ] && [ -z "$API_PORT" ] && [ "$NO_API" -eq 0 ]; then
    API_PORT="$(sed -n 's/.*:\([0-9]*\):8000".*/\1/p' "$RENGINE_HOME/ports.yml" 2>/dev/null | head -1)"
  fi

  ask_mode
  ask_reachability
  ask_api
  ask_admin

  if [ "$RECONFIGURE" -eq 1 ]; then
    update_env
    write_caddyfile
    write_ports
    refresh_keep
  else
    say ""
    say "Sized for $MEM_GB GB memory and $CPUS CPUs: $SCAN_SLOTS scan slots, $PG_SHARED_BUFFERS Postgres buffers."
    resolve_tag
    fetch_source
    write_files
  fi

  if [ "$NO_START" -eq 1 ]; then
    say ""
    say "Configuration written. Start with: rengine start"
    return 0
  fi

  deploy
  wait_healthy
  summary
}

main
