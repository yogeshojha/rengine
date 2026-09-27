"""Status of every downloaded dataset."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.datasets import DATASETS, DATASETS_BY_KIND, DatasetSpec
from shared.definitions.mode_features import has_capability
from shared.definitions.threat_intel import FEED_STATUS_LABELS
from shared.enums.instance import InstanceMode
from shared.models.dataset import DatasetRead, DatasetSyncResult
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings
from shared.models.threat_intel import ThreatFeed
from shared.services import locks
from shared.services.celery_dispatch import dispatch_dataset_sync
from shared.services.feed_ledger import dataset_status
from shared.utils.datetime import utc_now

PROBE_LOCK_TIMEOUT = "300ms"

_HELD_SQL = text("""
SELECT objid::bigint
FROM pg_locks
WHERE locktype = 'advisory'
  AND granted
  AND classid = 0
  AND objsubid = 1
  AND database = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND objid::bigint = ANY(:keys)
""")


class DatasetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _mode(self) -> str:
        found = await self.session.scalar(
            select(InstanceSettings.mode).where(
                InstanceSettings.singleton_key == SINGLETON_KEY
            )
        )
        return found or InstanceMode.BUG_BOUNTY.value

    async def _specs(self) -> list[DatasetSpec]:
        mode = await self._mode()
        return [
            spec
            for spec in DATASETS
            if spec.capability is None or has_capability(mode, spec.capability)
        ]

    async def _loading(self, specs: list[DatasetSpec]) -> set[str]:
        keys = {locks.dataset(spec.kind): spec.kind for spec in specs}
        held = await self.session.execute(_HELD_SQL, {"keys": list(keys)})
        return {keys[row[0]] for row in held}

    async def _rows(self, spec: DatasetSpec) -> int | None:
        where = f" WHERE {spec.where}" if spec.where else ""
        try:
            async with self.session.begin_nested():
                await self.session.execute(
                    text(f"SET LOCAL lock_timeout = '{PROBE_LOCK_TIMEOUT}'")
                )
                counted = await self.session.scalar(
                    text(f"SELECT count(*) FROM {spec.table}{where}")  # noqa: S608
                )
        except DBAPIError:
            return None
        return int(counted or 0)

    async def list(self) -> list[DatasetRead]:
        specs = await self._specs()
        loading = await self._loading(specs)
        ledger = {
            row.kind: row
            for row in (await self.session.execute(select(ThreatFeed))).scalars()
        }
        now = utc_now()
        out: list[DatasetRead] = []
        for spec in specs:
            busy = spec.kind in loading
            rows = None if busy else await self._rows(spec)
            row = ledger.get(spec.kind)
            state = dataset_status(
                loading=busy or rows is None,
                recorded=row.status if row else None,
                synced_at=row.last_synced_at if row else None,
                present=bool(rows),
                stale_after_hours=spec.stale_after_hours,
                now=now,
            )
            out.append(
                DatasetRead(
                    kind=spec.kind,
                    label=spec.label,
                    description=spec.description,
                    rows_noun=spec.rows_noun,
                    status=state,
                    status_label=FEED_STATUS_LABELS.get(state, state),
                    rows=rows or None,
                    error=row.error if row else None,
                    last_synced_at=row.last_synced_at if row else None,
                    last_attempt_at=row.last_attempt_at if row else None,
                    duration_ms=row.duration_ms if row else None,
                    auto_sync=spec.auto_sync,
                )
            )
        return out

    async def sync(self, kind: str) -> DatasetSyncResult:
        spec = DATASETS_BY_KIND.get(kind)
        if spec is None or spec not in await self._specs():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found."
            )
        queued = dispatch_dataset_sync(spec.task, dict(spec.task_kwargs))
        return DatasetSyncResult(
            queued=queued,
            detail=None
            if queued
            else "The task queue did not accept the download. "
            "Check that the worker services are running.",
        )
