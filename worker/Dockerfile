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

COPY shared /app/shared

COPY worker/pyproject.toml worker/uv.lock* ./

RUN uv sync --no-install-project

CMD ["uv", "run", "celery", "-A", "app.celery", "worker", "--loglevel=INFO"]


###################################################################
# TODO: Production
###################################################################
