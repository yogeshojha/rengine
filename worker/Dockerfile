FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_NO_SYNC=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv


##################################################################
# Tool build
##################################################################

FROM base AS gotools

# libpcap-dev builds naabu
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

ARG GO_SHA256_AMD64=12e6d6a191091ae27dc31f6efc630e3a3b8ba409baf3573d955b196fdf086005
ARG GO_SHA256_ARM64=ba611a53534135a81067240eff9508cd7e256c560edd5d8c2fef54f083c07129
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) sha="${GO_SHA256_AMD64}" ;; \
      arm64) sha="${GO_SHA256_ARM64}" ;; \
      *) echo "unsupported arch $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/go.tar.gz "https://go.dev/dl/go1.25.7.linux-${arch}.tar.gz"; \
    echo "${sha}  /tmp/go.tar.gz" | sha256sum -c -; \
    tar -C /usr/local -xzf /tmp/go.tar.gz; \
    rm -f /tmp/go.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}" \
    GOBIN=/out/bin \
    GOCACHE=/cache/build \
    GOMODCACHE=/cache/mod \
    GOFLAGS=-ldflags=-s

RUN --mount=type=cache,target=/cache/build --mount=type=cache,target=/cache/mod \
    go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@v1.3.1 \
    && go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.16.0 \
    && go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@v1.4.0 \
    && go install -v github.com/projectdiscovery/alterx/cmd/alterx@v0.1.0 \
    && go install -v github.com/tomnomnom/assetfinder@v0.1.1 \
    && go install -v github.com/gwen001/github-subdomains@v1.2.2 \
    && go install -v github.com/owasp-amass/amass/v4/...@v4.2.0

RUN --mount=type=cache,target=/cache/build --mount=type=cache,target=/cache/mod \
    go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@v2.6.1 \
    && go install -v github.com/projectdiscovery/httpx/cmd/httpx@v1.12.0 \
    && go install -v github.com/projectdiscovery/cdncheck/cmd/cdncheck@v1.3.0

RUN --mount=type=cache,target=/cache/build --mount=type=cache,target=/cache/mod \
    go install -v github.com/ffuf/ffuf/v2@v2.3.0 \
    && go install -v github.com/projectdiscovery/katana/cmd/katana@v1.7.0 \
    && go install -v github.com/projectdiscovery/urlfinder/cmd/urlfinder@v0.0.3

# nuclei, with templates synced at runtime onto the vuln-templates volume
RUN --mount=type=cache,target=/cache/build --mount=type=cache,target=/cache/mod \
    go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@v3.11.1

# certificate transparency stream for program watches
RUN --mount=type=cache,target=/cache/build --mount=type=cache,target=/cache/mod \
    go install -v software.sslmate.com/src/certspotter/cmd/certspotter@v0.24.2

# dalfox v3 release binary
ARG DALFOX_VERSION=v3.2.2
ARG DALFOX_SHA256_AMD64=7f9621090ab2c5ef48dbab3e2d7a9de81a54390efee2aaa0b431130df629715e
ARG DALFOX_SHA256_ARM64=020fd8605441b06931d4d6f149d5f97a9057d290db614c4671678eb50b612c42
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) slug="linux-x86_64"; sha="${DALFOX_SHA256_AMD64}" ;; \
      arm64) slug="linux-aarch64"; sha="${DALFOX_SHA256_ARM64}" ;; \
      *) echo "unsupported arch $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/dalfox.tar.gz "https://github.com/hahwul/dalfox/releases/download/${DALFOX_VERSION}/dalfox-${DALFOX_VERSION}-${slug}.tar.gz"; \
    echo "${sha}  /tmp/dalfox.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/dalfox.tar.gz -C /tmp; \
    mv "/tmp/dalfox-${DALFOX_VERSION}-${slug}/dalfox" /out/bin/dalfox; \
    rm -rf /tmp/dalfox.tar.gz "/tmp/dalfox-${DALFOX_VERSION}-${slug}"; \
    chmod +x /out/bin/dalfox; \
    /out/bin/dalfox --version

# julius and its MCP probe
ARG JULIUS_VERSION=v1.4.19
ARG JULIUS_SHA256_AMD64=021b9d32e7cea643bc2d05b1d2fe98ba1076e577435711a0f931bd0a0bc26f4b
ARG JULIUS_SHA256_ARM64=a031edffe64b703e2ef3f89b8a791c12204ca15d368a15982691644f1824cd16
ARG JULIUS_SRC_SHA256=732b08889c06b0cfd8ba9dcd8edad953b0dc45ef19eb49d3bb4365a6beed0899
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) sha="${JULIUS_SHA256_AMD64}" ;; \
      arm64) sha="${JULIUS_SHA256_ARM64}" ;; \
      *) echo "unsupported arch $arch" >&2; exit 1 ;; \
    esac; \
    v="${JULIUS_VERSION#v}"; \
    curl -fsSL -o /tmp/julius.tar.gz "https://github.com/praetorian-inc/julius/releases/download/${JULIUS_VERSION}/julius_${v}_linux_${arch}.tar.gz"; \
    echo "${sha}  /tmp/julius.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/julius.tar.gz -C /tmp julius; \
    mv /tmp/julius /out/bin/julius; \
    chmod +x /out/bin/julius; \
    curl -fsSL -o /tmp/julius-src.tar.gz "https://github.com/praetorian-inc/julius/archive/refs/tags/${JULIUS_VERSION}.tar.gz"; \
    echo "${JULIUS_SRC_SHA256}  /tmp/julius-src.tar.gz" | sha256sum -c -; \
    mkdir -p /out/julius/probes-mcp; \
    tar -xzf /tmp/julius-src.tar.gz -C /out/julius/probes-mcp --strip-components=2 "julius-${v}/probes/mcp-server.yaml"; \
    /out/bin/julius validate /out/julius/probes-mcp; \
    rm -f /tmp/julius.tar.gz /tmp/julius-src.tar.gz

# naabu's SYN scan as a non-root user
RUN apt-get update && apt-get install -y --no-install-recommends libcap2-bin \
    && rm -rf /var/lib/apt/lists/* \
    && setcap cap_net_raw+eip /out/bin/naabu


##################################################################
# Development
##################################################################

FROM base AS development

# chromium screenshots, naabu's SYN scan dlopens libpcap, WeasyPrint text layout
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    libpcap0.8t64 \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --no-cache-dir --break-system-packages wafw00f==2.4.2

ARG RENGINE_UID=10001
RUN groupadd --gid "$RENGINE_UID" rengine \
    && useradd --uid "$RENGINE_UID" --gid rengine --create-home --shell /usr/sbin/nologin rengine

COPY --from=gotools /out/bin/ /usr/local/bin/
COPY --from=gotools /out/julius/ /opt/julius/
# every tool that starts chromium finds this first
COPY --chmod=755 worker/chrome.sh /usr/local/bin/chrome

COPY VERSION /app/VERSION
COPY shared /app/shared
COPY tools /app/tools

COPY worker/pyproject.toml worker/uv.lock ./

RUN uv sync --no-install-project --locked

CMD ["uv", "run", "celery", "-A", "app.celery", "worker"]


##################################################################
# Production
##################################################################

FROM development AS production

COPY worker/app /app/app
COPY stages /app/stages
COPY reports /app/reports
COPY interest /app/interest
COPY toolbox /app/toolbox

# a release build takes its version from the tag
ARG RENGINE_VERSION=""
RUN [ -z "$RENGINE_VERSION" ] || printf '%s\n' "$RENGINE_VERSION" > /app/VERSION

# mount points a fresh volume copies its owner from
RUN mkdir -p /app/scan_media /app/vuln-templates /app/wordlists /app/reports-out \
      /app/exports-out /app/report-fonts /app/beat-state /app/ct-state \
    && chown rengine:rengine /app/scan_media /app/vuln-templates /app/wordlists \
      /app/reports-out /app/exports-out /app/report-fonts /app/beat-state /app/ct-state \
    && find / -xdev -perm /6000 -type f -exec chmod a-s {} +

USER rengine

CMD ["uv", "run", "celery", "-A", "app.celery", "worker"]
