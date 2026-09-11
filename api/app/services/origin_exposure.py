"""The api's view of origin exposure."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.scan_correlation import OriginExposure
from shared.services.origin_exposure import OriginExposureService as _Engine


class OriginExposureService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def run(self, scan_id: UUID) -> OriginExposure:
        return await self.session.run_sync(lambda s: _Engine(s).run(scan_id))
