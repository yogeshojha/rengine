"""Proxy observations become endpoint rows of the target's covering scan."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import cast, func, select, update
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.connectors import BROWSING_RUN_LABEL, CandidateState
from shared.definitions.endpoints import EndpointSource
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanScope, ScanStatus
from shared.models.connector import Connector, ConnectorCandidate
from shared.models.endpoint import Endpoint
from shared.models.scan import Scan
from shared.services import endpoint_inventory
from shared.services.asset_query.lead_cache import bump_sync
from shared.services.endpoint_inventory import EndpointObservation, UpsertResult
from shared.services.endpoint_noise import NoisePolicy
from shared.services.scan_scope import census_only, covers
from shared.utils.datetime import utc_now
from shared.utils.text import counted

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from sqlmodel import SQLModel

_DIMENSION = SurfaceDimension.ENDPOINTS.value


def _started():
    return func.coalesce(Scan.started_at, Scan.created_at)


def covering_scan(
    session: Session,
    project_id: uuid.UUID,
    target_id: uuid.UUID,
    model: type[SQLModel],
    dimension: str,
) -> Scan | None:
    """The settled census scan the target's view of the dimension reads."""
    return session.scalar(
        select(Scan)
        .where(
            Scan.project_id == project_id,
            Scan.target_id == target_id,
            Scan.status.in_(SCAN_TERMINAL_STATUSES),
            census_only(),
            covers(model, dimension),
        )
        .order_by(_started().desc())
        .limit(1)
    )


def census_in_flight(
    session: Session, project_id: uuid.UUID, target_id: uuid.UUID
) -> bool:
    return (
        session.scalar(
            select(func.count())
            .select_from(Scan)
            .where(
                Scan.project_id == project_id,
                Scan.target_id == target_id,
                Scan.status.not_in(SCAN_TERMINAL_STATUSES),
                census_only(),
            )
        )
        or 0
    ) > 0


def holding_run(
    session: Session,
    *,
    project_id: uuid.UUID,
    target_id: uuid.UUID,
    label: str,
    owner: str,
    config: dict,
    created_by: uuid.UUID | None,
) -> Scan:
    """The completed full run keyed on config[owner] that holds rows for a target."""
    existing = session.scalar(
        select(Scan)
        .where(
            Scan.project_id == project_id,
            Scan.target_id == target_id,
            Scan.scope == ScanScope.FULL.value,
            cast(Scan.execution_config, JSONB)[owner].astext == config[owner],
        )
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        return existing
    now = utc_now()
    run = Scan(
        project_id=project_id,
        target_id=target_id,
        engine_id=None,
        engine_name=label[:200],
        scope=ScanScope.FULL.value,
        status=ScanStatus.COMPLETED.value,
        execution_config=config,
        started_at=now,
        completed_at=now,
        created_by=created_by,
    )
    session.add(run)
    session.flush()
    return run


def browsing_run(session: Session, connector: Connector, target_id: uuid.UUID) -> Scan:
    """The run that holds browsing for a target without a census scan."""
    return holding_run(
        session,
        project_id=connector.project_id,
        target_id=target_id,
        label=f"{BROWSING_RUN_LABEL} · {connector.name}",
        owner="connector",
        config={"manual": True, "connector": str(connector.id)},
        created_by=connector.created_by,
    )


def _observation(candidate: ConnectorCandidate) -> EndpointObservation:
    return EndpointObservation(
        url=candidate.url,
        detail=f"{counted(candidate.hits, 'request')} through {candidate.source_tool}",
        observed_at=candidate.last_seen_at,
        methods=list(candidate.methods or []),
        is_probed=candidate.status_code is not None,
        status_code=candidate.status_code,
        content_type=candidate.content_type,
        content_length=candidate.content_length,
        title=candidate.title,
    )


def write(
    session: Session,
    *,
    scan: Scan,
    candidates: list[ConnectorCandidate],
) -> UpsertResult:
    """Record the candidates as proxy-sourced endpoints of the scan."""
    rows = [c for c in candidates if c.state != CandidateState.IGNORED.value]
    if not rows:
        return UpsertResult()
    hosts = sorted({c.host for c in rows})
    result = endpoint_inventory.upsert(
        session,
        scan_id=scan.id,
        target_id=scan.target_id,
        project_id=scan.project_id,
        source=EndpointSource.PROXY.value,
        observations=[_observation(c) for c in rows],
        index=endpoint_inventory.build_index(session, scan.id, hosts),
        default_scheme="http",
        policy=NoisePolicy.protected(),
    )
    if result.created or result.updated:
        bump_sync([scan.target_id])
    return result


def sync_target(
    session: Session,
    *,
    connector: Connector,
    target_id: uuid.UUID,
    candidates: list[ConnectorCandidate],
) -> UpsertResult | None:
    """Write into the covering scan. Defer while a census scan is running."""
    scan = covering_scan(session, connector.project_id, target_id, Endpoint, _DIMENSION)
    if scan is None:
        if census_in_flight(session, connector.project_id, target_id):
            return None
        scan = browsing_run(session, connector, target_id)
    return write(session, scan=scan, candidates=candidates)


def replay(session: Session, scan: Scan) -> UpsertResult | None:
    """Write every recorded shape of the target into the scan."""
    if scan.scope != ScanScope.FULL.value:
        return None
    if not session.scalar(
        select(covers(Endpoint, _DIMENSION)).where(Scan.id == scan.id)
    ):
        return None
    candidates = (
        session.execute(
            select(ConnectorCandidate).where(
                ConnectorCandidate.project_id == scan.project_id,
                ConnectorCandidate.target_id == scan.target_id,
            )
        )
        .scalars()
        .all()
    )
    if not candidates:
        return None
    return write(session, scan=scan, candidates=list(candidates))


def settle_queue(session: Session, scan: Scan) -> int:
    """Mark the shapes queued for this scan as scanned."""
    result = session.execute(
        update(ConnectorCandidate)
        .where(
            ConnectorCandidate.scan_id == scan.id,
            ConnectorCandidate.state == CandidateState.QUEUED.value,
        )
        .values(state=CandidateState.SCANNED.value)
    )
    session.commit()
    return result.rowcount or 0
