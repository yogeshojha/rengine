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
    # a service banner is whatever the socket sent back, bytes and all
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


def upsert(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    source: str,
    observations: list[ServiceObservation],
    batch: int = 1000,
    keep_source: bool = False,
    replace: bool = False,
) -> int:
    """Merge observations into ports. Never loses a field a weaker source already filled.

    replace drops this source's earlier rows in the same transaction as the insert, so a
    re-running stage never leaves the table short of what it already knew.
    """
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
    # a stable key order keeps concurrent overlapping upserts from deadlocking
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

    for start in range(0, len(rows), batch):
        statement = insert(Port).values(rows[start : start + batch])
        excluded = statement.excluded
        stronger = _rank(excluded.source) >= _rank(Port.source)
        origin = (
            Port.source
            if keep_source
            else case((stronger, excluded.source), else_=Port.source)
        )
        session.execute(
            statement.on_conflict_do_update(
                constraint=_CONSTRAINT,
                set_={
                    "state": case((stronger, excluded.state), else_=Port.state),
                    "service_name": func.coalesce(
                        excluded.service_name, Port.service_name
                    ),
                    "service_class": case(
                        (
                            excluded.service_class != ServiceClass.OTHER.value,
                            excluded.service_class,
                        ),
                        else_=Port.service_class,
                    ),
                    "source": origin,
                    "is_http": or_(Port.is_http, excluded.is_http),
                    "tls": or_(Port.tls, excluded.tls),
                    "product": func.coalesce(excluded.product, Port.product),
                    "version": func.coalesce(excluded.version, Port.version),
                    "banner": func.coalesce(excluded.banner, Port.banner),
                    "cpe": case(
                        (func.json_array_length(excluded.cpe) > 0, excluded.cpe),
                        else_=Port.cpe,
                    ),
                    "discovered_at": func.least(
                        Port.discovered_at, excluded.discovered_at
                    ),
                },
            )
        )
    session.commit()
    return len(rows)
