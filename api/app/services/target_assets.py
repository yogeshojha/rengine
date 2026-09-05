from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.enums.scan import SCAN_LIVE_STATUSES
from shared.models.http_asset import HttpAsset
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.target_asset import (
    TargetAssetFacets,
    TargetAssetFilter,
    TargetAssetPage,
    TargetAssetRow,
)


class TargetAssetService:
    """The target's web assets rolled up across every scan that found them."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def page(
        self, project_id: UUID, target_id: UUID, f: TargetAssetFilter
    ) -> TargetAssetPage:
        live = await self._live_scans(project_id, target_id)
        latest = await self._latest_scan(project_id, target_id, live)
        if latest is None and not live:
            return TargetAssetPage()

        baseline = latest is not None and await self._has_baseline(
            project_id, target_id, latest
        )
        rolled = self._rollup(project_id, target_id, latest, live, baseline).subquery(
            "rolled"
        )
        facets = await self._facets(rolled, latest, baseline)

        scoped = select(rolled).where(*self._predicates(rolled, f))
        total = await self.session.scalar(
            select(func.count()).select_from(scoped.subquery())
        )
        rows = await self.session.execute(
            self._ordered(scoped, rolled, f).limit(f.limit).offset(f.offset)
        )
        return TargetAssetPage(
            items=[_to_row(r) for r in rows.mappings().all()],
            total=int(total or 0),
            facets=facets,
        )

    async def _live_scans(self, project_id: UUID, target_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(Scan.id).where(
                Scan.project_id == project_id,
                Scan.target_id == target_id,
                Scan.status.in_(SCAN_LIVE_STATUSES),
            )
        )
        return list(result.scalars().all())

    async def _latest_scan(
        self, project_id: UUID, target_id: UUID, live: list[UUID]
    ) -> UUID | None:
        """Newest finished scan that found web assets — a live run cannot retire anything."""
        query = select(Subdomain.scan_id).where(
            Subdomain.project_id == project_id, Subdomain.target_id == target_id
        )
        if live:
            query = query.where(Subdomain.scan_id.notin_(live))
        return await self.session.scalar(
            query.order_by(
                Subdomain.discovered_at.desc(), Subdomain.scan_id.desc()
            ).limit(1)
        )

    async def _has_baseline(
        self, project_id: UUID, target_id: UUID, latest: UUID
    ) -> bool:
        earlier = await self.session.scalar(
            select(Subdomain.id)
            .where(
                Subdomain.project_id == project_id,
                Subdomain.target_id == target_id,
                Subdomain.scan_id != latest,
            )
            .limit(1)
        )
        return earlier is not None

    def _rollup(
        self,
        project_id: UUID,
        target_id: UUID,
        latest: UUID | None,
        live: list[UUID],
        baseline: bool,
    ) -> Select:
        scope = (Subdomain.project_id == project_id, Subdomain.target_id == target_id)
        seen_now = [Subdomain.scan_id == latest] if latest else []
        if live:
            seen_now.append(Subdomain.scan_id.in_(live))
        agg = (
            select(
                Subdomain.name.label("name"),
                func.min(Subdomain.discovered_at).label("first_seen"),
                func.max(Subdomain.discovered_at).label("last_seen"),
                func.count(func.distinct(Subdomain.scan_id)).label("scan_count"),
                func.bool_or(or_(*seen_now) if seen_now else literal(True)).label(
                    "current"
                ),
            )
            .where(*scope)
            .group_by(Subdomain.name)
            .subquery("agg")
        )
        # the newest row per name carries the attributes worth showing
        newest = (
            select(Subdomain)
            .where(*scope)
            .distinct(Subdomain.name)
            .order_by(
                Subdomain.name, Subdomain.discovered_at.desc(), Subdomain.scan_id.desc()
            )
            .subquery("newest")
        )
        web = (
            select(HttpAsset)
            .where(HttpAsset.target_id == target_id)
            .distinct(HttpAsset.host)
            .order_by(
                HttpAsset.host,
                HttpAsset.discovered_at.desc(),
                HttpAsset.status_code.asc().nullslast(),
            )
            .subquery("web")
        )
        return (
            select(
                agg.c.name,
                agg.c.first_seen,
                agg.c.last_seen,
                agg.c.scan_count,
                agg.c.current,
                and_(agg.c.current, agg.c.scan_count == 1, literal(baseline)).label(
                    "is_new"
                ),
                newest.c.is_active,
                newest.c.is_wildcard,
                newest.c.resolved_ips,
                newest.c.cname,
                newest.c.sources,
                newest.c.scan_id.label("last_scan_id"),
                web.c.status_code,
                web.c.title,
                web.c.webserver,
                web.c.tech,
                web.c.ip,
                web.c.asn_org,
                web.c.is_cdn,
                web.c.cdn_name,
                web.c.screenshot_path,
            )
            .select_from(agg)
            .join(newest, newest.c.name == agg.c.name)
            .outerjoin(web, web.c.host == agg.c.name)
        )

    @staticmethod
    def _predicates(rolled, f: TargetAssetFilter) -> list[ColumnElement[bool]]:
        where: list[ColumnElement[bool]] = []
        if f.search:
            needle = f"%{f.search.strip().lower()}%"
            where.append(
                or_(
                    func.lower(rolled.c.name).like(needle),
                    func.lower(func.coalesce(rolled.c.title, "")).like(needle),
                    func.lower(func.coalesce(rolled.c.ip, "")).like(needle),
                )
            )
        if f.state == "current":
            where.append(rolled.c.current.is_(True))
        elif f.state == "gone":
            where.append(rolled.c.current.is_(False))
        elif f.state == "new":
            where.append(rolled.c.is_new.is_(True))
        if f.live:
            where.append(rolled.c.status_code.isnot(None))
        return where

    @staticmethod
    def _ordered(query: Select, rolled, f: TargetAssetFilter) -> Select:
        columns = {
            "name": rolled.c.name,
            "first_seen": rolled.c.first_seen,
            "last_seen": rolled.c.last_seen,
            "scans": rolled.c.scan_count,
            "status": rolled.c.status_code,
        }
        column = columns.get(f.sort, rolled.c.name)
        direction = column.asc() if f.order == "asc" else column.desc()
        return query.order_by(direction.nullslast(), rolled.c.name.asc())

    async def _facets(
        self, rolled, latest: UUID | None, baseline: bool
    ) -> TargetAssetFacets:
        row = await self.session.execute(
            select(
                func.count().label("total"),
                func.count().filter(rolled.c.current.is_(True)).label("current"),
                func.count().filter(rolled.c.is_new.is_(True)).label("new"),
                func.count().filter(rolled.c.current.is_(False)).label("gone"),
                func.count().filter(rolled.c.status_code.isnot(None)).label("live"),
            ).select_from(rolled)
        )
        counts = row.mappings().one()
        return TargetAssetFacets(
            total=counts["total"],
            current=counts["current"],
            new=counts["new"],
            gone=counts["gone"],
            live=counts["live"],
            baseline=not baseline,
            latest_scan_id=latest,
        )


def _to_row(m) -> TargetAssetRow:
    return TargetAssetRow(
        name=m["name"],
        is_active=bool(m["is_active"]),
        is_wildcard=bool(m["is_wildcard"]),
        resolved_ips=list(m["resolved_ips"] or []),
        cname=m["cname"],
        sources=list(m["sources"] or []),
        scan_count=m["scan_count"],
        first_seen=m["first_seen"],
        last_seen=m["last_seen"],
        last_scan_id=m["last_scan_id"],
        current=bool(m["current"]),
        is_new=bool(m["is_new"]),
        status_code=m["status_code"],
        title=m["title"],
        webserver=m["webserver"],
        tech=list(m["tech"] or []),
        ip=m["ip"],
        asn_org=m["asn_org"],
        is_cdn=bool(m["is_cdn"]),
        cdn_name=m["cdn_name"],
        screenshot_path=m["screenshot_path"],
    )
