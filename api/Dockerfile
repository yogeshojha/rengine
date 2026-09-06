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

COPY api/pyproject.toml api/uv.lock* ./

RUN uv sync --no-install-project

# Expose port
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--reload-dir", "/app/app", \
     "--reload-dir", "/app/shared", \
     "--reload-dir", "/app/tools", \
     "--reload-dir", "/app/stages", \
     "--reload-dir", "/app/reports", \
     "--timeout-graceful-shutdown", "2"]

##################################################################
# TODO: Production
##################################################################
