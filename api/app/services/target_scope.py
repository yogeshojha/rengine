from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.scan import Scan
from shared.models.tag import TargetTag
from shared.models.target import Target, TargetOrganization


@dataclass(frozen=True)
class TargetFilter:
    """Targets named directly, by organization or by tag."""

    target_ids: tuple[UUID, ...] = ()
    organization_id: UUID | None = None
    tag_id: UUID | None = None

    @property
    def active(self) -> bool:
        return bool(self.target_ids or self.organization_id or self.tag_id)


Targets = frozenset[UUID] | None


async def resolve_targets(
    session: AsyncSession, project_id: UUID | None, spec: TargetFilter | None
) -> Targets:
    """The project's targets the filter keeps, or None when nothing is filtered."""
    if project_id is None or spec is None or not spec.active:
        return None
    query = select(Target.id).where(Target.project_id == project_id)
    if spec.target_ids:
        query = query.where(Target.id.in_(spec.target_ids))
    if spec.organization_id:
        query = query.where(
            Target.id.in_(
                select(TargetOrganization.target_id).where(
                    TargetOrganization.organization_id == spec.organization_id
                )
            )
        )
    if spec.tag_id:
        query = query.where(
            Target.id.in_(
                select(TargetTag.target_id).where(TargetTag.tag_id == spec.tag_id)
            )
        )
    return frozenset((await session.execute(query)).scalars().all())


def keeps(targets: Targets, target_id: UUID | None) -> bool:
    return targets is None or target_id in targets


async def require_scan(session: AsyncSession, project_id: UUID, scan_id: UUID) -> None:
    """Refuse a scan outside the project."""
    owner = await session.scalar(select(Scan.project_id).where(Scan.id == scan_id))
    if owner != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Scan not found.")


async def require_target(
    session: AsyncSession,
    project_id: UUID,
    target_id: UUID,
    scan_id: UUID | None = None,
) -> None:
    """Refuse a target outside the project, or a scan of another target."""
    owned = await session.scalar(
        select(Target.id).where(Target.id == target_id, Target.project_id == project_id)
    )
    if owned is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Target not found.")
    if scan_id is None:
        return
    scan = await session.scalar(
        select(Scan.id).where(
            Scan.id == scan_id,
            Scan.target_id == target_id,
            Scan.project_id == project_id,
        )
    )
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Scan not found.")
