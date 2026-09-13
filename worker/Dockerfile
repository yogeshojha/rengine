FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    C_FORCE_ROOT=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv


##################################################################
# Development
##################################################################

FROM base AS development

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://go.dev/dl/go1.25.7.linux-amd64.tar.gz | tar -C /usr/local -xzf -
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"


RUN go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@v1.3.1 \
    && go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.16.0 \
    && go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@v1.4.0 \
    && go install -v github.com/projectdiscovery/alterx/cmd/alterx@v0.1.0 \
    && go install -v github.com/tomnomnom/assetfinder@v0.1.1 \
    && go install -v github.com/gwen001/github-subdomains@v1.2.2 \
    && go install -v github.com/owasp-amass/amass/v4/...@v4.2.0

# naabu needs libpcap
RUN apt-get update && apt-get install -y --no-install-recommends libpcap-dev \
    && rm -rf /var/lib/apt/lists/* \
    && go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@v2.6.1 \
    && go install -v github.com/projectdiscovery/httpx/cmd/httpx@v1.12.0 \
    && go install -v github.com/projectdiscovery/cdncheck/cmd/cdncheck@v1.3.0

# ffuf, chromium for screenshots, wafw00f
RUN apt-get update && apt-get install -y --no-install-recommends chromium \
    && rm -rf /var/lib/apt/lists/* \
    && go install -v github.com/ffuf/ffuf/v2@v2.3.0 \
    && python3 -m pip install --no-cache-dir --break-system-packages wafw00f

# url discovery
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@v1.7.0 \
    && go install -v github.com/projectdiscovery/urlfinder/cmd/urlfinder@v0.0.3

# nuclei, with templates synced at runtime onto the vuln-templates volume
RUN go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@v3.11.1

# certificate transparency stream for program watches
RUN go install -v software.sslmate.com/src/certspotter/cmd/certspotter@v0.24.2


# WeasyPrint and its text layout
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY shared /app/shared
COPY tools /app/tools
COPY stages /app/stages
COPY reports /app/reports
COPY interest /app/interest
COPY toolbox /app/toolbox

COPY worker/pyproject.toml worker/uv.lock* ./

RUN uv sync --no-install-project

CMD ["uv", "run", "celery", "-A", "app.celery", "worker", "--loglevel=INFO"]


# a prod stage must COPY stages/ and reports/ and keep PYTHONPATH=/app
