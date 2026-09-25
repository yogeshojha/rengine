"""Lookalike domains of one scan or a target's newest run, with their triage."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.lookalikes import (
    LOOKALIKE_STAGE,
    THREAT_VERDICTS,
    VERDICT_ORDER,
    VERDICT_RANK,
    LookalikeState,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanActivityStatus
from shared.models.lookalike import (
    LookalikeDomain,
    LookalikeRead,
    LookalikeSummary,
    LookalikeTriage,
)
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now

MAX_ROWS = 1000
_COVERING = (ScanActivityStatus.SUCCESS.value, ScanActivityStatus.PARTIAL.value)


def _read(row: LookalikeDomain, state: str) -> LookalikeRead:
    return LookalikeRead(
        id=row.id,
        scan_id=row.scan_id,
        target_id=row.target_id,
        apex=row.apex,
        domain=row.domain,
        display=row.display,
        technique=row.technique,
        verdict=row.verdict,
        link_reason=row.link_reason,
        a=list(row.a or []),
        aaaa=list(row.aaaa or []),
        mx=list(row.mx or []),
        ns=list(row.ns or []),
        parked=row.parked,
        http_status=row.http_status,
        final_url=row.final_url,
        title=row.title,
        similarity=row.similarity,
        registered_at=row.registered_at,
        registrar=row.registrar,
        first_seen=row.first_seen,
        discovered_at=row.discovered_at,
        state=state,
    )


class LookalikeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def for_scan(self, project_id: UUID, scan_id: UUID) -> LookalikeSummary:
        activity = (
            await self.session.execute(
                select(ScanActivity.status, ScanActivity.result).where(
                    ScanActivity.scan_id == scan_id,
                    ScanActivity.project_id == project_id,
                    ScanActivity.name == LOOKALIKE_STAGE,
                )
            )
        ).first()
        rows = (
            (
                await self.session.execute(
                    select(LookalikeDomain).where(
                        LookalikeDomain.project_id == project_id,
                        LookalikeDomain.scan_id == scan_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        summary = LookalikeSummary(scan_id=scan_id)
        if activity is not None:
            result = activity.result or {}
            summary.permutations = result.get("permutations")
            summary.fetched = bool(result.get("pages_fetched"))
        summary.covered = bool(rows) or (
            activity is not None and activity.status in _COVERING
        )
        if not rows:
            return summary

        target_id = rows[0].target_id
        states = dict(
            (
                await self.session.execute(
                    select(LookalikeTriage.domain, LookalikeTriage.state).where(
                        LookalikeTriage.target_id == target_id,
                        LookalikeTriage.domain.in_([r.domain for r in rows]),
                    )
                )
            ).all()
        )
        ordered = sorted(
            rows,
            key=lambda r: (
                VERDICT_RANK.get(r.verdict, len(VERDICT_ORDER)),
                -(r.similarity or 0),
                -(r.registered_at.timestamp() if r.registered_at else 0),
                r.domain,
            ),
        )
        reads = [
            _read(r, states.get(r.domain, LookalikeState.OPEN.value))
            for r in ordered[:MAX_ROWS]
        ]
        summary.target_id = target_id
        summary.apex = rows[0].apex
        summary.observed_at = max(r.discovered_at for r in rows)
        summary.rows = reads
        summary.registered = len(rows)
        summary.verdicts = {
            key: sum(1 for r in rows if r.verdict == key) for key in VERDICT_ORDER
        }
        summary.open_threats = sum(
            1
            for r in rows
            if r.verdict in THREAT_VERDICTS
            and states.get(r.domain, LookalikeState.OPEN.value)
            == LookalikeState.OPEN.value
        )
        return summary

    async def for_target(self, project_id: UUID, target_id: UUID) -> LookalikeSummary:
        """The target's newest settled census run that checked lookalikes."""
        scan_id = (
            await self.session.execute(
                select(Scan.id)
                .join(ScanActivity, ScanActivity.scan_id == Scan.id)
                .where(
                    Scan.project_id == project_id,
                    Scan.target_id == target_id,
                    Scan.status.in_(SCAN_TERMINAL_STATUSES),
                    census_only(),
                    ScanActivity.name == LOOKALIKE_STAGE,
                    ScanActivity.status.in_(_COVERING),
                )
                .order_by(Scan.started_at.desc().nulls_last())
                .limit(1)
            )
        ).scalar_one_or_none()
        if scan_id is None:
            return LookalikeSummary(target_id=target_id)
        summary = await self.for_scan(project_id, scan_id)
        summary.target_id = target_id
        return summary

    async def triage(
        self, project_id: UUID, target_id: UUID, domains: list[str], state: str
    ) -> int:
        clean = sorted({d.strip().lower() for d in domains if d.strip()})
        if not clean:
            return 0
        now = utc_now()
        stmt = insert(LookalikeTriage).values(
            [
                {
                    "id": uuid.uuid4(),
                    "project_id": project_id,
                    "target_id": target_id,
                    "domain": domain,
                    "state": state,
                    "updated_at": now,
                }
                for domain in clean
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_lookalike_triage_target_domain",
            set_={"state": stmt.excluded.state, "updated_at": stmt.excluded.updated_at},
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return len(clean)


__all__ = ["LookalikeService"]
