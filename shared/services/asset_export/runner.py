"""One export run: the filtered set the table shows, streamed to a file."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select, text

from shared.definitions.exports import (
    EXPORT_CHUNK,
    MAX_EXPORT_ROWS,
    ExportFormat,
)
from shared.definitions.surface import SurfaceDimension
from shared.services.asset_export import columns as cols
from shared.services.asset_export import enrich, writer
from shared.services.asset_query.errors import NO_JIT
from shared.services.surface_query import for_dimension

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import datetime
    from pathlib import Path
    from uuid import UUID

    from sqlalchemy.orm import Session

    from shared.services.asset_query import QueryScope

# an export is a background job, so it does not take the api's 20s read ceiling
EXPORT_TIMEOUT = "SET LOCAL statement_timeout = '600s'"


@dataclass
class ExportResult:
    rows: int
    total: int
    capped: bool
    bytes_written: int


@contextmanager
def _stream(session: Session, statement, chunk: int):
    """A cursor of its own: a commit or a join on the session would invalidate it."""
    connection = session.get_bind().connect()
    try:
        connection.execute(text(EXPORT_TIMEOUT))
        connection.execute(text(NO_JIT))
        result = connection.execute(statement.execution_options(yield_per=chunk))
        yield result.mappings()
    finally:
        connection.close()


def _ip_of(dimension: str, row: dict) -> list[str]:
    if dimension == SurfaceDimension.WEB_ASSETS.value:
        return list(row.get("resolved_ips") or [])
    return [row["ip"]] if row.get("ip") else []


def _fill_joined(
    session: Session, scope: QueryScope, dimension: str, chunk: list[dict]
) -> None:
    joined = cols.JOINED.get(dimension, frozenset())
    if not joined:
        return
    addresses = {ip for row in chunk for ip in _ip_of(dimension, row)}
    ports = enrich.ports_for(session, scope, addresses) if "ports" in joined else {}
    hosts = enrich.hosts_for(session, scope, addresses) if "hosts" in joined else {}
    for row in chunk:
        ips = _ip_of(dimension, row)
        if "ports" in joined:
            row["ports"] = sorted({n for ip in ips for n in ports.get(ip, ())})
        if "hosts" in joined:
            row["hosts"] = sorted({h for ip in ips for h in hosts.get(ip, ())})


def run(
    session: Session,
    *,
    dimension: str,
    scope: QueryScope,
    filters: dict,
    now: datetime,
    export_format: str,
    path: Path,
    project_id: UUID | None = None,
    on_progress: Callable[[int, str], None] | None = None,
) -> ExportResult:
    query = for_dimension(dimension)
    f = query.filter_model.model_validate(filters or {})
    built = query.filtered(
        scope, f, now, project_id=project_id, columns=cols.columns_for(dimension, scope)
    )

    session.execute(text(EXPORT_TIMEOUT))
    session.execute(text(NO_JIT))

    total = session.scalar(
        select(func.count()).select_from(
            built.statement.limit(MAX_EXPORT_ROWS + 1).subquery()
        )
    )
    total = int(total or 0)
    capped = total > MAX_EXPORT_ROWS
    if on_progress:
        on_progress(10, f"Reading {min(total, MAX_EXPORT_ROWS)} rows")

    statement = query.order(built, f, scope).limit(MAX_EXPORT_ROWS)
    headers = cols.headers(dimension)

    def stream() -> Iterator[dict]:
        with _stream(session, statement, EXPORT_CHUNK) as rows:
            chunk: list[dict] = []
            seen = 0
            for row in rows:
                chunk.append(cols.project(row, headers))
                if len(chunk) < EXPORT_CHUNK:
                    continue
                _fill_joined(session, scope, dimension, chunk)
                yield from chunk
                seen += len(chunk)
                chunk = []
                if on_progress:
                    share = min(90, 10 + int(80 * seen / max(total, 1)))
                    on_progress(share, f"Wrote {seen} rows")
            if chunk:
                _fill_joined(session, scope, dimension, chunk)
                yield from chunk

    if export_format == ExportFormat.TXT.value:
        written = writer.write_txt(
            path, (cols.text_values(dimension, row) for row in stream())
        )
    elif export_format == ExportFormat.JSON.value:
        written = writer.write_json(path, headers, stream())
    else:
        written = writer.write_csv(path, headers, stream())

    return ExportResult(
        rows=written,
        total=total,
        capped=capped,
        bytes_written=path.stat().st_size if path.exists() else 0,
    )
