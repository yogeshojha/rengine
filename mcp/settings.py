"""Server settings, stored on instance_settings like every other instance switch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mcp.capabilities import DEFAULT_CEILING
from shared.utils.datetime import utc_now

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOLS: tuple[str, ...] = ("2026-07-28", "2025-06-18", "2025-03-26")
SERVER_NAME = "rengine"
HTTP_PATH = "/api/v1/mcp"
DEFAULT_RATE_LIMIT = 120

_CEILING = "ceiling"
_RATE = "rate_limit_per_minute"
_STARTED = "started_at"


@dataclass
class ServerSettings:
    enabled: bool = False
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT
    ceiling: dict[str, bool] = None  # type: ignore[assignment]
    started_at: datetime | None = None

    def __post_init__(self) -> None:
        self.ceiling = {**DEFAULT_CEILING, **(self.ceiling or {})}


def read(row) -> ServerSettings:
    blob = dict(getattr(row, "mcp_settings", None) or {})
    started = blob.get(_STARTED)
    return ServerSettings(
        enabled=bool(getattr(row, "mcp_enabled", False)),
        rate_limit_per_minute=int(blob.get(_RATE, DEFAULT_RATE_LIMIT)),
        ceiling={**DEFAULT_CEILING, **(blob.get(_CEILING) or {})},
        started_at=_parse(started),
    )


def write(row, settings: ServerSettings) -> None:
    row.mcp_enabled = settings.enabled
    row.mcp_settings = {
        _RATE: settings.rate_limit_per_minute,
        _CEILING: settings.ceiling,
        _STARTED: settings.started_at.isoformat() if settings.started_at else None,
    }
    row.updated_at = utc_now()


def _parse(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def endpoint_url(ui_base: str) -> str:
    return f"{ui_base.rstrip('/')}{HTTP_PATH}"


def stdio_command() -> str:
    return "docker compose exec -T api /app/.venv/bin/python -m mcp.stdio"
