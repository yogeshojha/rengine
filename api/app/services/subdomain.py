from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging import get_logger
from shared.models.subdomain import (
    Subdomain,
    SubdomainRead,
    SubdomainSummary,
    TargetSubdomainRead,
)

logger = get_logger(__name__)

_TARGET_ROLLUP_CAP = 20000


class SubdomainService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_read(self, sub: Subdomain) -> SubdomainRead:
        return SubdomainRead(
            id=sub.id,
            scan_id=sub.scan_id,
            target_id=sub.target_id,
            name=sub.name,
            sources=list(sub.sources or []),
            resolved_ips=list(sub.resolved_ips or []),
            cname=sub.cname,
            is_active=sub.is_active,
            is_wildcard=sub.is_wildcard,
            is_excluded=sub.is_excluded,
            is_important=sub.is_important,
            http_url=sub.http_url,
            http_status=sub.http_status,
            page_title=sub.page_title,
            content_type=sub.content_type,
            content_length=sub.content_length,
            response_time=sub.response_time,
            webserver=sub.webserver,
            tech=list(sub.tech or []),
            is_cdn=sub.is_cdn,
            cdn_name=sub.cdn_name,
            screenshot_path=sub.screenshot_path,
            discovered_at=sub.discovered_at,
        )

    def _base_query(
        self,
        project_id: UUID,
        scan_id: UUID | None,
        target_id: UUID | None,
        active_only: bool,
        search: str | None,
    ):
        query = select(Subdomain).where(Subdomain.project_id == project_id)
        if scan_id is not None:
            query = query.where(Subdomain.scan_id == scan_id)
        if target_id is not None:
            query = query.where(Subdomain.target_id == target_id)
        if active_only:
            query = query.where(Subdomain.is_active == True)  # noqa: E712
        if search:
            query = query.where(Subdomain.name.ilike(f"%{search}%"))
        return query

    async def list(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
        active_only: bool = False,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SubdomainRead]:
        query = self._base_query(project_id, scan_id, target_id, active_only, search)
        query = query.order_by(Subdomain.name).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_read(s) for s in result.scalars().all()]

    async def summary(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> SubdomainSummary:
        query = self._base_query(project_id, scan_id, target_id, False, None)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        source_counts: Counter = Counter()
        active = 0
        for row in rows:
            if row.is_active:
                active += 1
            for src in row.sources or []:
                source_counts[src] += 1
        return SubdomainSummary(
            total=len(rows), active=active, sources=dict(source_counts)
        )

    async def _fetch_target_rows(
        self, project_id: UUID, target_id: UUID
    ) -> list[Subdomain]:
        query = (
            select(Subdomain)
            .where(Subdomain.project_id == project_id, Subdomain.target_id == target_id)
            .order_by(Subdomain.discovered_at.desc(), Subdomain.scan_id.desc())
            .limit(_TARGET_ROLLUP_CAP + 1)
        )
        result = await self.session.execute(query)
        rows = list(result.scalars().all())
        if len(rows) > _TARGET_ROLLUP_CAP:
            logger.warning(
                "target %s rollup capped at %d rows (newest kept)",
                target_id,
                _TARGET_ROLLUP_CAP,
            )
            rows = rows[:_TARGET_ROLLUP_CAP]
        # fetched newest-first to keep the latest scan under the cap; _aggregate
        # needs ascending so the newest row wins on overwrite (deterministic tie-break)
        rows.sort(key=lambda r: (r.discovered_at, str(r.scan_id)))
        return rows

    @staticmethod
    def _aggregate(rows: list[Subdomain]) -> dict[str, TargetSubdomainRead]:
        agg: dict[str, TargetSubdomainRead] = {}
        scan_ids: dict[str, set] = {}
        for (
            row
        ) in rows:  # ordered by discovered_at asc, so latest row wins on overwrite
            existing = agg.get(row.name)
            if existing is None:
                scan_ids[row.name] = {row.scan_id}
                agg[row.name] = TargetSubdomainRead(
                    name=row.name,
                    sources=list(row.sources or []),
                    resolved_ips=list(row.resolved_ips or []),
                    cname=row.cname,
                    is_active=row.is_active,
                    is_wildcard=row.is_wildcard,
                    is_excluded=row.is_excluded,
                    scan_count=1,
                    last_scan_id=row.scan_id,
                    first_seen=row.discovered_at,
                    last_seen=row.discovered_at,
                )
                continue
            scan_ids[row.name].add(row.scan_id)
            existing.sources = sorted(set(existing.sources) | set(row.sources or []))
            existing.resolved_ips = list(row.resolved_ips or [])
            existing.cname = row.cname
            existing.is_active = row.is_active
            existing.is_wildcard = row.is_wildcard
            existing.is_excluded = row.is_excluded
            existing.last_scan_id = row.scan_id
            existing.last_seen = row.discovered_at
            existing.scan_count = len(scan_ids[row.name])
        return agg

    async def list_for_target(
        self,
        project_id: UUID,
        target_id: UUID,
        active_only: bool = False,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TargetSubdomainRead]:
        rows = await self._fetch_target_rows(project_id, target_id)
        items = list(self._aggregate(rows).values())
        if active_only:
            items = [i for i in items if i.is_active]
        if search:
            needle = search.lower()
            items = [i for i in items if needle in i.name.lower()]
        items.sort(key=lambda i: i.name)
        return items[offset : offset + limit]

    async def summary_for_target(
        self, project_id: UUID, target_id: UUID
    ) -> SubdomainSummary:
        rows = await self._fetch_target_rows(project_id, target_id)
        agg = self._aggregate(rows)
        source_counts: Counter = Counter()
        active = 0
        for item in agg.values():
            if item.is_active:
                active += 1
            for src in item.sources:
                source_counts[src] += 1
        return SubdomainSummary(
            total=len(agg), active=active, sources=dict(source_counts)
        )

    async def count(
        self,
        project_id: UUID,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> int:
        query = select(func.count()).select_from(
            self._base_query(project_id, scan_id, target_id, False, None).subquery()
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())
