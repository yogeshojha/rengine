"""Tags a person puts on scans to group runs."""

import uuid
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.scan import Scan
from shared.models.scan_tag import (
    ScanTag,
    ScanTagAssignment,
    ScanTagLink,
    ScanTagRead,
    ScanTagSummary,
)


class ScanTagService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_project(self, project_id: uuid.UUID) -> list[ScanTagRead]:
        rows = await self.session.execute(
            select(ScanTag.id, ScanTag.name, func.count(ScanTagLink.scan_id))
            .join(ScanTagLink, ScanTagLink.tag_id == ScanTag.id)
            .where(ScanTag.project_id == project_id)
            .group_by(ScanTag.id, ScanTag.name)
            .order_by(ScanTag.name)
        )
        return [
            ScanTagRead(id=tid, name=name, scan_count=n) for tid, name, n in rows.all()
        ]

    async def summaries(
        self, scan_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[ScanTagSummary]]:
        if not scan_ids:
            return {}
        rows = await self.session.execute(
            select(ScanTagLink.scan_id, ScanTag.id, ScanTag.name)
            .join(ScanTag, ScanTag.id == ScanTagLink.tag_id)
            .where(ScanTagLink.scan_id.in_(scan_ids))
            .order_by(ScanTag.name)
        )
        out: dict[uuid.UUID, list[ScanTagSummary]] = defaultdict(list)
        for sid, tid, name in rows.all():
            out[sid].append(ScanTagSummary(id=tid, name=name))
        return out

    async def ensure(
        self, project_id: uuid.UUID, names: list[str], user_id: uuid.UUID | None
    ) -> list[uuid.UUID]:
        if not names:
            return []
        await self.session.execute(
            insert(ScanTag)
            .values(
                [
                    {
                        "id": uuid.uuid4(),
                        "project_id": project_id,
                        "name": name,
                        "created_by": user_id,
                    }
                    for name in names
                ]
            )
            .on_conflict_do_nothing(constraint="uq_scan_tags_project_name")
        )
        return list(
            (
                await self.session.execute(
                    select(ScanTag.id).where(
                        ScanTag.project_id == project_id, ScanTag.name.in_(names)
                    )
                )
            ).scalars()
        )

    async def change(
        self,
        project_id: uuid.UUID,
        scan_ids: list[uuid.UUID],
        add: list[str],
        remove: list[str],
        user_id: uuid.UUID | None,
    ) -> list[ScanTagAssignment]:
        owned = list(
            (
                await self.session.execute(
                    select(Scan.id).where(
                        Scan.project_id == project_id, Scan.id.in_(scan_ids)
                    )
                )
            ).scalars()
        )
        if len(owned) != len(set(scan_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
            )
        if remove:
            await self.session.execute(
                delete(ScanTagLink).where(
                    ScanTagLink.scan_id.in_(owned),
                    ScanTagLink.tag_id.in_(
                        select(ScanTag.id).where(
                            ScanTag.project_id == project_id, ScanTag.name.in_(remove)
                        )
                    ),
                )
            )
        tag_ids = await self.ensure(project_id, add, user_id)
        if tag_ids:
            await self.session.execute(
                insert(ScanTagLink)
                .values([{"scan_id": s, "tag_id": t} for s in owned for t in tag_ids])
                .on_conflict_do_nothing()
            )
        await self.session.commit()
        tags = await self.summaries(owned)
        return [ScanTagAssignment(scan_id=s, tags=tags.get(s, [])) for s in owned]
