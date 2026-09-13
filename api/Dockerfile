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
COPY stages /app/stages
COPY reports /app/reports
COPY interest /app/interest
COPY mcp /app/mcp
COPY connectors /app/connectors
COPY toolbox /app/toolbox
COPY binaries /app/binaries

COPY api/pyproject.toml api/uv.lock* ./

RUN uv sync --no-install-project

EXPOSE 8000

COPY api/entrypoint.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
