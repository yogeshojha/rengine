FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    C_FORCE_ROOT=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv


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


RUN go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest \
    && go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
    && go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@latest \
    && go install -v github.com/tomnomnom/assetfinder@latest \
    && go install -v github.com/owasp-amass/amass/v4/...@master

# Expansion-phase tools (naabu needs libpcap)
RUN apt-get update && apt-get install -y --no-install-recommends libpcap-dev \
    && rm -rf /var/lib/apt/lists/* \
    && go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest \
    && go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest \
    && go install -v github.com/projectdiscovery/cdncheck/cmd/cdncheck@latest


COPY shared /app/shared
COPY tools /app/tools
COPY engines /app/engines

COPY worker/pyproject.toml worker/uv.lock* ./

RUN uv sync --no-install-project

CMD ["uv", "run", "celery", "-A", "app.celery", "worker", "--loglevel=INFO"]


###################################################################
# TODO: Production
# NOTE: engines/ resolves via PYTHONPATH=/app (not a packaged dep) —
# the prod stage MUST `COPY engines /app/engines` and keep PYTHONPATH=/app.
###################################################################
