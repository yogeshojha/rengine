from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


NO_FILTER = TargetFilter()

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
