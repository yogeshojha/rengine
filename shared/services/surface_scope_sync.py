"""The scans a dimension reads, resolved from sync code the way the api resolves them."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.new_checks import NEW_CHECKS_KEY
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import ScanScope, ScanStatus
from shared.models.scan import Scan
from shared.services.asset_query import QueryScope
from shared.services.scan_deltas import TABLES
from shared.services.scan_scope import census_only, covers

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def _started():
    return func.coalesce(Scan.started_at, Scan.created_at)


def _follow_ups(session: Session, project_id: UUID, picks) -> list[UUID]:
    """New-checks runs completed after each target's census pick."""
    if not picks:
        return []
    at_by_target = {row.target_id: row.at for row in picks}
    rows = session.execute(
        select(Scan.id, Scan.target_id, _started().label("at")).where(
            Scan.project_id == project_id,
            Scan.scope == ScanScope.FOCUSED.value,
            Scan.status == ScanStatus.COMPLETED.value,
            cast(Scan.execution_config, JSONB).has_key(NEW_CHECKS_KEY),
            Scan.target_id.in_(list(at_by_target)),
        )
    ).all()
    return [
        row.id
        for row in rows
        if row.at is not None and row.at > at_by_target[row.target_id]
    ]


def _scope(
    session: Session, project_id: UUID, dimension: str, target_id=None
) -> QueryScope:
    picks = _picks(session, project_id, dimension, target_id)
    ids = [row.id for row in picks]
    if dimension == SurfaceDimension.VULNERABILITIES.value:
        ids.extend(_follow_ups(session, project_id, picks))
    return QueryScope(tuple(ids), project_id=project_id)


def _picks(session: Session, project_id: UUID, dimension: str, target_id=None):
    """The newest scan of each target that actually ran this dimension."""
    statement = (
        select(Scan.id, Scan.target_id, _started().label("at"))
        .where(
            Scan.project_id == project_id,
            census_only(),
            covers(TABLES[dimension], dimension),
        )
        .distinct(Scan.target_id)
        .order_by(Scan.target_id, _started().desc())
    )
    if target_id is not None:
        statement = statement.where(Scan.target_id == target_id)
    return session.execute(statement).all()


def project_scope(session: Session, project_id: UUID, dimension: str) -> QueryScope:
    return _scope(session, project_id, dimension)


def target_scope(
    session: Session, project_id: UUID, target_id: UUID, dimension: str
) -> QueryScope:
    return _scope(session, project_id, dimension, target_id)
