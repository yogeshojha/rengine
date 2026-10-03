FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_NO_SYNC=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv


##################################################################
# Development
##################################################################

FROM base AS development

COPY VERSION /app/VERSION
COPY shared /app/shared
COPY tools /app/tools

COPY api/pyproject.toml api/uv.lock ./

RUN uv sync --no-install-project --locked

EXPOSE 8000

COPY api/entrypoint.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]


##################################################################
# Production
##################################################################

FROM development AS production

RUN uv sync --no-install-project --locked --no-dev

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

# same uid as the worker image
ARG RENGINE_UID=10001
RUN groupadd --gid "$RENGINE_UID" rengine \
    && useradd --uid "$RENGINE_UID" --gid rengine --create-home --shell /usr/sbin/nologin rengine \
    && mkdir -p /app/scan_media /app/vuln-templates /app/wordlists /app/reports-out \
      /app/exports-out /app/report-fonts \
    && chown rengine:rengine /app/scan_media /app/vuln-templates /app/wordlists \
      /app/reports-out /app/exports-out /app/report-fonts \
    && find / -xdev -perm /6000 -type f -exec chmod a-s {} +

ENV API_RELOAD=false

USER rengine

CMD ["/app/entrypoint.sh"]
