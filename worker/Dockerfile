FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    C_FORCE_ROOT=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv


##################################################################
# Tool build: only /out/bin reaches the runtime image
##################################################################

FROM base AS gotools

# libpcap-dev builds naabu
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://go.dev/dl/go1.25.7.linux-$(dpkg --print-architecture).tar.gz" | tar -C /usr/local -xzf -

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

# dalfox v3 is a Rust binary, shipped as a release tarball rather than go install
ARG DALFOX_VERSION=v3.2.2
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) slug="linux-x86_64" ;; \
      arm64) slug="linux-aarch64" ;; \
      *) echo "unsupported arch $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/dalfox.tar.gz "https://github.com/hahwul/dalfox/releases/download/${DALFOX_VERSION}/dalfox-${DALFOX_VERSION}-${slug}.tar.gz"; \
    tar -xzf /tmp/dalfox.tar.gz -C /tmp; \
    mv "/tmp/dalfox-${DALFOX_VERSION}-${slug}/dalfox" /out/bin/dalfox; \
    rm -rf /tmp/dalfox.tar.gz "/tmp/dalfox-${DALFOX_VERSION}-${slug}"; \
    chmod +x /out/bin/dalfox; \
    /out/bin/dalfox --version


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
    && python3 -m pip install --no-cache-dir --break-system-packages wafw00f

COPY --from=gotools /out/bin/ /root/go/bin/
ENV PATH="/root/go/bin:${PATH}"

COPY shared /app/shared
COPY tools /app/tools

COPY worker/pyproject.toml worker/uv.lock* ./

RUN uv sync --no-install-project

CMD ["uv", "run", "celery", "-A", "app.celery", "worker", "--loglevel=INFO"]


##################################################################
# Production: what dev mounts from the host is copied in
##################################################################

FROM development AS production

COPY worker/app /app/app
COPY stages /app/stages
COPY reports /app/reports
COPY interest /app/interest
COPY toolbox /app/toolbox

CMD ["uv", "run", "celery", "-A", "app.celery", "worker", "--loglevel=INFO"]
