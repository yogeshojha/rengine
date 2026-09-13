"""The scans a dimension reads, resolved from sync code the way the api resolves them."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from shared.definitions.surface import SurfaceDimension
from shared.models.endpoint import Endpoint
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import QueryScope
from shared.services.scan_scope import census_only, covers

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

TABLES = {
    SurfaceDimension.WEB_ASSETS.value: Subdomain,
    SurfaceDimension.ENDPOINTS.value: Endpoint,
    SurfaceDimension.SERVICES.value: Port,
    SurfaceDimension.IPS.value: IpAddress,
    SurfaceDimension.VULNERABILITIES.value: Vulnerability,
    SurfaceDimension.SOFTWARE.value: SoftwareCve,
}


def _started():
    return func.coalesce(Scan.started_at, Scan.created_at)


def _picks(session: Session, project_id: UUID, dimension: str, target_id=None):
    """The newest scan of each target that actually ran this dimension."""
    statement = (
        select(Scan.id, Scan.target_id)
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
    return QueryScope(
        tuple(row.id for row in _picks(session, project_id, dimension)),
        project_id=project_id,
    )


def target_scope(
    session: Session, project_id: UUID, target_id: UUID, dimension: str
) -> QueryScope:
    return QueryScope(
        tuple(row.id for row in _picks(session, project_id, dimension, target_id)),
        project_id=project_id,
    )
