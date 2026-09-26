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

# the lockfile is required: a build resolves exactly what was locked and tested
COPY api/pyproject.toml api/uv.lock ./

RUN uv sync --locked --no-install-project

EXPOSE 8000

COPY api/entrypoint.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]


##################################################################
# Production: what dev mounts from the host is copied in
##################################################################

FROM development AS production

# compose's &api-volumes, as copies; `make check-lists` keeps the two in step
COPY api/app /app/app
COPY stages /app/stages
COPY reports /app/reports
COPY interest /app/interest
COPY mcp /app/mcp
COPY channels /app/channels
COPY connectors /app/connectors
COPY toolbox /app/toolbox
COPY binaries /app/binaries
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

ENV API_RELOAD=false

CMD ["/app/entrypoint.sh"]
