FROM python:3.13-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv


##################################################################
# Development
##################################################################

FROM base AS development

# Copy shared directory inside the app
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

# Expose port
EXPOSE 8000

COPY api/entrypoint.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
