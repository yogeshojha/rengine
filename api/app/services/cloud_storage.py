"""Cloud buckets of one scan or a target's newest run, with their triage."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.cloud_storage import (
    ACCESS_ORDER,
    ACCESS_RANK,
    CLOUD_STORAGE_STAGE,
    OPEN_ACCESS,
    PROVIDER_ORDER,
    SOURCE_RANK,
    ReviewState,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanActivityStatus
from shared.models.cloud_storage import (
    CloudBucket,
    CloudBucketRead,
    CloudBucketSummary,
    CloudBucketTriage,
)
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now

MAX_ROWS = 1000
_COVERING = (ScanActivityStatus.SUCCESS.value, ScanActivityStatus.PARTIAL.value)


def _read(row: CloudBucket, state: str) -> CloudBucketRead:
    return CloudBucketRead(
        id=row.id,
        scan_id=row.scan_id,
        target_id=row.target_id,
        name=row.name,
        provider=row.provider,
        url=row.url,
        source=row.source,
        access=row.access,
        region=row.region,
        object_count=row.object_count,
        size=row.size,
        first_seen=row.first_seen,
        discovered_at=row.discovered_at,
        state=state,
    )


class CloudStorageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def for_scan(self, project_id: UUID, scan_id: UUID) -> CloudBucketSummary:
        activity = (
            await self.session.execute(
                select(ScanActivity.status, ScanActivity.result).where(
                    ScanActivity.scan_id == scan_id,
                    ScanActivity.project_id == project_id,
                    ScanActivity.name == CLOUD_STORAGE_STAGE,
                )
            )
        ).first()
        rows = (
            (
                await self.session.execute(
                    select(CloudBucket).where(
                        CloudBucket.project_id == project_id,
                        CloudBucket.scan_id == scan_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        summary = CloudBucketSummary(scan_id=scan_id)
        if activity is not None:
            summary.candidates = (activity.result or {}).get("candidates")
        summary.covered = bool(rows) or (
            activity is not None and activity.status in _COVERING
        )
        if not rows:
            return summary

        target_id = rows[0].target_id
        states = (
            await self.session.execute(
                select(
                    CloudBucketTriage.provider,
                    CloudBucketTriage.name,
                    CloudBucketTriage.state,
                ).where(
                    CloudBucketTriage.target_id == target_id,
                    CloudBucketTriage.name.in_([r.name for r in rows]),
                )
            )
        ).all()
        state_of = {(p, n): s for p, n, s in states}
        ordered = sorted(
            rows,
            key=lambda r: (
                ACCESS_RANK.get(r.access, len(ACCESS_ORDER)),
                SOURCE_RANK.get(r.source, 9),
                r.provider,
                r.name,
            ),
        )
        reads = [
            _read(r, state_of.get((r.provider, r.name), ReviewState.OPEN.value))
            for r in ordered[:MAX_ROWS]
        ]
        summary.target_id = target_id
        summary.observed_at = max(r.discovered_at for r in rows)
        summary.rows = reads
        summary.total = len(rows)
        summary.open_count = sum(1 for r in rows if r.access in OPEN_ACCESS)
        summary.access_counts = {
            key: sum(1 for r in rows if r.access == key) for key in ACCESS_ORDER
        }
        summary.provider_counts = {
            key: sum(1 for r in rows if r.provider == key) for key in PROVIDER_ORDER
        }
        return summary

    async def for_target(self, project_id: UUID, target_id: UUID) -> CloudBucketSummary:
        """The target's newest settled census run that checked cloud storage."""
        scan_id = (
            await self.session.execute(
                select(Scan.id)
                .join(ScanActivity, ScanActivity.scan_id == Scan.id)
                .where(
                    Scan.project_id == project_id,
                    Scan.target_id == target_id,
                    Scan.status.in_(SCAN_TERMINAL_STATUSES),
                    census_only(),
                    ScanActivity.name == CLOUD_STORAGE_STAGE,
                    ScanActivity.status.in_(_COVERING),
                )
                .order_by(Scan.started_at.desc().nulls_last())
                .limit(1)
            )
        ).scalar_one_or_none()
        if scan_id is None:
            return CloudBucketSummary(target_id=target_id)
        summary = await self.for_scan(project_id, scan_id)
        summary.target_id = target_id
        return summary

    async def triage(
        self,
        project_id: UUID,
        target_id: UUID,
        buckets: list[tuple[str, str]],
        state: str,
    ) -> int:
        clean = sorted(
            {
                (p.strip().lower(), n.strip().lower())
                for p, n in buckets
                if p.strip() and n.strip()
            }
        )
        if not clean:
            return 0
        now = utc_now()
        stmt = insert(CloudBucketTriage).values(
            [
                {
                    "id": uuid.uuid4(),
                    "project_id": project_id,
                    "target_id": target_id,
                    "provider": provider,
                    "name": name,
                    "state": state,
                    "updated_at": now,
                }
                for provider, name in clean
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_cloud_bucket_triage_target_provider_name",
            set_={"state": stmt.excluded.state, "updated_at": stmt.excluded.updated_at},
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return len(clean)


__all__ = ["CloudStorageService"]
