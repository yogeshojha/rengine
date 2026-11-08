"""Service observations merged into the ports table, whatever stage saw them."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import case, delete, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func

from shared.definitions.ports import (
    PORT_SOURCE_RANK,
    PortState,
    ServiceClass,
    likely_tls,
    service_class,
    service_for_port,
)
from shared.models.port import Port
from shared.utils.datetime import utc_now
from shared.utils.text import scrub

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_CONSTRAINT = "uq_port_scan_ip_num_proto"
_BATCH = 1000
_TABLE = Port.__table__


@dataclass
class ServiceObservation:
    ip: str
    port: int
    protocol: str = "tcp"
    state: str = PortState.OPEN.value
    tls: bool = False
    is_http: bool = False
    service_name: str | None = None
    product: str | None = None
    version: str | None = None
    banner: str | None = None
    cpe: list[str] = field(default_factory=list)


def _rank(column):
    return case(PORT_SOURCE_RANK, value=column, else_=0)


def _row(
    obs: ServiceObservation,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    source: str,
    now,
) -> dict:
    name = obs.service_name or service_for_port(obs.port)
    tls = obs.tls or likely_tls(obs.port)
    return scrub(
        {
            "id": uuid.uuid4(),
            "scan_id": scan_id,
            "target_id": target_id,
            "project_id": project_id,
            "ip": obs.ip,
            "number": obs.port,
            "protocol": obs.protocol,
            "state": obs.state,
            "service_name": name,
            "service_class": service_class(name, obs.port, is_http=obs.is_http),
            "source": source,
            "is_http": obs.is_http,
            "tls": tls,
            "product": obs.product,
            "version": obs.version,
            "banner": obs.banner,
            "cpe": list(obs.cpe or []),
            "discovered_at": now,
            "created_at": now,
        }
    )


def _upsert_statement(keep_source: bool):
    statement = insert(_TABLE)
    excluded = statement.excluded
    stronger = _rank(excluded.source) >= _rank(_TABLE.c.source)
    origin = (
        _TABLE.c.source
        if keep_source
        else case((stronger, excluded.source), else_=_TABLE.c.source)
    )
    return statement.on_conflict_do_update(
        constraint=_CONSTRAINT,
        set_={
            "state": case((stronger, excluded.state), else_=_TABLE.c.state),
            "service_name": func.coalesce(excluded.service_name, _TABLE.c.service_name),
            "service_class": case(
                (
                    excluded.service_class != ServiceClass.OTHER.value,
                    excluded.service_class,
                ),
                else_=_TABLE.c.service_class,
            ),
            "source": origin,
            "is_http": or_(_TABLE.c.is_http, excluded.is_http),
            "tls": or_(_TABLE.c.tls, excluded.tls),
            "product": func.coalesce(excluded.product, _TABLE.c.product),
            "version": func.coalesce(excluded.version, _TABLE.c.version),
            "banner": func.coalesce(excluded.banner, _TABLE.c.banner),
            "cpe": case(
                (func.json_array_length(excluded.cpe) > 0, excluded.cpe),
                else_=_TABLE.c.cpe,
            ),
            "discovered_at": func.least(_TABLE.c.discovered_at, excluded.discovered_at),
        },
    )


def upsert(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    source: str,
    observations: list[ServiceObservation],
    keep_source: bool = False,
    replace: bool = False,
) -> int:
    """Merge observations into ports."""
    if replace:
        session.execute(
            delete(Port).where(Port.scan_id == scan_id, Port.source == source)
        )
    if not observations:
        session.commit()
        return 0
    now = utc_now()
    seen: dict[tuple[str, int, str], ServiceObservation] = {}
    for obs in observations:
        seen[(obs.ip, obs.port, obs.protocol)] = obs
    ordered = [seen[key] for key in sorted(seen)]
    rows = [
        _row(
            obs,
            scan_id=scan_id,
            target_id=target_id,
            project_id=project_id,
            source=source,
            now=now,
        )
        for obs in ordered
    ]

    statement = _upsert_statement(keep_source)
    for start in range(0, len(rows), _BATCH):
        session.execute(statement, rows[start : start + _BATCH])
    session.commit()
    return len(rows)
