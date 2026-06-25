from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.port import Port, PortRead, PortSummary


class PortService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_read(self, port: Port) -> PortRead:
        return PortRead(
            id=port.id,
            scan_id=port.scan_id,
            target_id=port.target_id,
            ip=port.ip,
            number=port.number,
            protocol=port.protocol,
            state=port.state,
            service_name=port.service_name,
            source=port.source,
            discovered_at=port.discovered_at,
        )

    def _base_query(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        search: str | None,
    ):
        query = select(Port).where(Port.project_id == project_id)
        if scan_id is not None:
            query = query.where(Port.scan_id == scan_id)
        if target_id is not None:
            query = query.where(Port.target_id == target_id)
        if search:
            query = query.where(Port.ip.ilike(f"%{search}%"))
        return query

    async def list(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
        search: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[PortRead]:
        query = self._base_query(project_id, scan_id, target_id, search)
        query = query.order_by(Port.ip, Port.number).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_read(p) for p in result.scalars().all()]

    async def summary(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> PortSummary:
        query = self._base_query(project_id, scan_id, target_id, None)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        by_service: Counter = Counter()
        for row in rows:
            by_service[row.service_name or "unknown"] += 1
        return PortSummary(total=len(rows), by_service=dict(by_service))
