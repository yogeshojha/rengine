FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv


##################################################################
# Development
##################################################################

FROM base AS development

COPY shared /app/shared
COPY tools /app/tools

COPY api/pyproject.toml api/uv.lock* ./

RUN uv sync --no-install-project

EXPOSE 8000

COPY api/entrypoint.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]


# stages/, reports/, interest/, mcp/, connectors/, toolbox/ and binaries/ are mounted in
# dev; a prod stage must COPY them and keep PYTHONPATH=/app
