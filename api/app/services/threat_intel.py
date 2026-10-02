"""Read side of the exploitation intelligence: feed state, coverage, per-CVE detail."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import case, exists, func, literal_column, not_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.asset_query import VULN_FLAGS, VULN_QUERY
from shared.definitions.threat_intel import (
    BANDS_BY_KEY,
    EXPLOIT_BANDS,
    FEED_STATUS_LABELS,
    FEEDS,
    SIGNALS_BY_KIND,
    VULNX_PROVIDER,
    ExploitSignal,
    FeedStatus,
    exploit_band,
)
from shared.enums.api_key import APIProvider
from shared.models.api_key import APIKey
from shared.models.target import Target
from shared.models.threat_intel import (
    CveIntelRead,
    ExposureProduct,
    FindingIntel,
    IntelChange,
    IntelCoverage,
    IntelSignal,
    KevDetail,
    PocRef,
    SignalFinding,
    SignalRead,
    ThreatFeedRead,
    ThreatIntelStatus,
    ThreatProviderRead,
)
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import (
    QueryScope,
    VulnQueryContext,
    compile_vuln_query,
    parse_query,
    vuln_suppressed,
)
from shared.services.threat_intel import feed_status
from shared.utils.datetime import utc_now

STALE_INTEL_DAYS = 2

_CHANGE_KINDS = (
    ExploitSignal.KEV.value,
    ExploitSignal.RANSOM_PATH.value,
    ExploitSignal.FRESH_EXPLOIT.value,
    ExploitSignal.WEAPONISED.value,
)


def _band():
    return case(
        *[
            (Vulnerability.epss_score >= band.floor, band.key)
            for band in EXPLOIT_BANDS[:-1]
        ],
        else_=EXPLOIT_BANDS[-1].key,
    )


def _flag(name: str, scope: QueryScope):
    """The vulnerability grammar's `is:<name>`."""
    return compile_vuln_query(
        parse_query(f"is:{name}", VULN_QUERY),
        VulnQueryContext(scope=scope, now=utc_now()),
    )


def _signalled(kind: str, scope: QueryScope):
    if kind in VULN_FLAGS:
        return _flag(kind, scope)
    return exists(
        select(1).where(
            IntelSignal.vulnerability_id == Vulnerability.id, IntelSignal.kind == kind
        )
    )


class ThreatIntelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _reach(scope: QueryScope | None) -> list:
        """The findings a scope's vulnerabilities page lists."""
        if scope is None:
            return []
        return [scope.match(Vulnerability.scan_id), not_(vuln_suppressed(scope))]

    async def coverage(self, scope: QueryScope | None = None) -> IntelCoverage:
        reach = self._reach(scope)
        flags = scope or QueryScope(())
        n = func.count()
        row = (
            await self.session.execute(
                select(
                    n,
                    n.filter(Vulnerability.epss_score.isnot(None)),
                    n.filter(_flag("kev", flags)),
                    n.filter(_flag("ransomware", flags)),
                    n.filter(_flag("weaponised", flags)),
                ).where(*reach)
            )
        ).one()
        band = _band().label("band")
        bands = {
            key: int(count)
            for key, count in await self.session.execute(
                select(band, func.count())
                .where(Vulnerability.epss_score.isnot(None), *reach)
                .group_by(literal_column("band"))
            )
        }
        findings, scored, kev, ransomware, weaponised = (int(v or 0) for v in row)
        return IntelCoverage(
            findings=findings,
            scored=scored,
            kev=kev,
            ransomware=ransomware,
            weaponised=weaponised,
            bands=bands,
        )

    async def feeds(self) -> list[ThreatFeedRead]:
        rows = {
            r.kind: r
            for r in (
                await self.session.execute(
                    text(
                        "SELECT kind, status, rows, version, bytes, duration_ms, error,"
                        " last_synced_at FROM threat_feeds"
                    )
                )
            ).all()
        }
        counted = " UNION ALL ".join(
            f"SELECT '{spec.kind}' AS k, count(*) AS n FROM {spec.rows_table}"  # noqa: S608
            for spec in FEEDS
        )
        counts = dict((await self.session.execute(text(counted))).all())
        out: list[ThreatFeedRead] = []
        for spec in FEEDS:
            row = rows.get(spec.kind)
            status = feed_status(row, int(counts.get(spec.kind, 0)))
            out.append(
                ThreatFeedRead(
                    kind=spec.kind,
                    label=spec.label,
                    tagline=spec.tagline,
                    description=spec.description,
                    source=spec.source,
                    source_url=spec.source_url,
                    url=spec.url,
                    license=spec.license,
                    rows_noun=spec.rows_noun,
                    status=status,
                    status_label=FEED_STATUS_LABELS.get(status, status),
                    rows=int(counts.get(spec.kind, 0)),
                    version=row.version if row else None,
                    bytes=int(row.bytes) if row else 0,
                    duration_ms=int(row.duration_ms) if row else 0,
                    error=row.error if row else None,
                    last_synced_at=row.last_synced_at if row else None,
                )
            )
        return out

    async def changes(
        self,
        scope: QueryScope | None,
        *,
        days: int = 7,
        limit: int = 20,
    ) -> list[IntelChange]:
        rows = await self.session.execute(
            select(
                IntelSignal.vulnerability_id,
                IntelSignal.kind,
                IntelSignal.created_at,
                Vulnerability.scan_id,
                Vulnerability.target_id,
                Vulnerability.template_name,
                Vulnerability.severity,
                Vulnerability.host,
                Vulnerability.matched_at,
                Vulnerability.epss_score,
                Vulnerability.cve_ids,
                Target.target_value,
            )
            .join(Vulnerability, Vulnerability.id == IntelSignal.vulnerability_id)
            .join(Target, Target.id == Vulnerability.target_id)
            .where(
                IntelSignal.kind.in_(_CHANGE_KINDS),
                IntelSignal.created_at > utc_now() - timedelta(days=days),
                *self._reach(scope),
            )
            .order_by(IntelSignal.created_at.desc())
            .limit(limit)
        )
        return [
            IntelChange(
                vulnerability_id=r.vulnerability_id,
                scan_id=r.scan_id,
                target_id=r.target_id,
                target_value=r.target_value,
                template_name=r.template_name,
                severity=r.severity,
                cve=(r.cve_ids or [""])[0] if r.cve_ids else "",
                host=r.host,
                matched_at=r.matched_at,
                change=r.kind,
                epss_after=r.epss_score,
                changed_at=r.created_at,
            )
            for r in rows
        ]

    async def signal_findings(
        self,
        kind: str,
        scope: QueryScope | None,
        *,
        limit: int = 100,
    ) -> list[SignalFinding]:
        """`kind` may name several signals."""
        kinds = [k.strip() for k in kind.split(",") if k.strip()]
        if not kinds:
            return []
        flags = scope or QueryScope(())
        reason = (
            select(IntelSignal.reason)
            .where(
                IntelSignal.vulnerability_id == Vulnerability.id,
                IntelSignal.kind.in_(kinds),
            )
            .order_by(IntelSignal.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        rows = await self.session.execute(
            select(
                Vulnerability.id,
                Vulnerability.scan_id,
                Vulnerability.target_id,
                Vulnerability.template_name,
                Vulnerability.severity,
                Vulnerability.host,
                Vulnerability.matched_at,
                Vulnerability.epss_score,
                Vulnerability.exploit_score,
                Vulnerability.cve_ids,
                Target.target_value,
                reason.label("reason"),
            )
            .join(Target, Target.id == Vulnerability.target_id)
            .where(or_(*[_signalled(k, flags) for k in kinds]), *self._reach(scope))
            .order_by(
                Vulnerability.exploit_score.desc().nulls_last(),
                Vulnerability.epss_score.desc().nulls_last(),
                Vulnerability.id,
            )
            .limit(limit)
        )
        return [
            SignalFinding(
                vulnerability_id=r.id,
                scan_id=r.scan_id,
                target_id=r.target_id,
                target_value=r.target_value,
                template_name=r.template_name,
                severity=r.severity,
                host=r.host,
                matched_at=r.matched_at,
                cve=(r.cve_ids or [""])[0] if r.cve_ids else "",
                epss_score=r.epss_score,
                exploit_score=int(r.exploit_score or 0),
                reason=r.reason or "",
            )
            for r in rows
        ]

    async def status(self, scope: QueryScope | None = None) -> ThreatIntelStatus:
        feeds = await self.feeds()
        coverage = await self.coverage(scope)
        cached, fetched = (
            await self.session.execute(
                text("SELECT count(*), max(fetched_at) FROM cve_intel")
            )
        ).one()
        has_key = bool(
            await self.session.scalar(
                select(APIKey.id)
                .where(
                    APIKey.provider == APIProvider.VULNX,
                    APIKey.is_enabled.is_(True),
                )
                .limit(1)
            )
        )
        auto = (
            await self.session.execute(
                text("SELECT threat_intel_auto_sync FROM instance_settings LIMIT 1")
            )
        ).scalar()
        return ThreatIntelStatus(
            auto_sync=True if auto is None else bool(auto),
            feeds=feeds,
            coverage=coverage,
            ready=all(
                f.status in (FeedStatus.READY.value, FeedStatus.STALE.value)
                for f in feeds
            ),
            syncing=any(f.status == FeedStatus.SYNCING.value for f in feeds),
            providers=[
                ThreatProviderRead(
                    kind=VULNX_PROVIDER.kind,
                    label=VULNX_PROVIDER.label,
                    tagline=VULNX_PROVIDER.tagline,
                    source=VULNX_PROVIDER.source,
                    source_url=VULNX_PROVIDER.source_url,
                    rows_noun=VULNX_PROVIDER.rows_noun,
                    rows=int(cached or 0),
                    keyed=has_key,
                    unkeyed_rate=VULNX_PROVIDER.unkeyed_rate,
                    last_fetched_at=fetched,
                )
            ],
        )

    async def set_auto_sync(self, enabled: bool) -> bool:
        await self.session.execute(
            text(
                "UPDATE instance_settings"
                " SET threat_intel_auto_sync = :v, updated_at = now()"
            ),
            {"v": enabled},
        )
        await self.session.commit()
        return enabled

    async def cve(self, cve_id: str) -> CveIntelRead:
        key = cve_id.strip().upper()[:30]
        epss = (
            await self.session.execute(
                text("SELECT score, percentile FROM epss_scores WHERE cve = :c"),
                {"c": key},
            )
        ).first()
        kev = (
            (
                await self.session.execute(
                    text("SELECT * FROM kev_entries WHERE cve = :c"), {"c": key}
                )
            )
            .mappings()
            .first()
        )
        detail = (
            (
                await self.session.execute(
                    text("SELECT * FROM cve_intel WHERE cve = :c"), {"c": key}
                )
            )
            .mappings()
            .first()
        )

        band = exploit_band(epss.score if epss else None)
        out = CveIntelRead(
            cve=key,
            epss_score=epss.score if epss else None,
            epss_percentile=epss.percentile if epss else None,
            band=band,
            band_label=BANDS_BY_KEY[band].label if band else None,
            is_kev=kev is not None,
        )
        if kev:
            due = kev.get("due_date")
            today = utc_now().date()
            out.kev = KevDetail(
                vendor=kev.get("vendor"),
                product=kev.get("product"),
                name=kev.get("name"),
                short_description=kev.get("short_description"),
                required_action=kev.get("required_action"),
                notes=kev.get("notes"),
                cwes=list(kev.get("cwes") or []),
                known_ransomware=bool(kev.get("known_ransomware")),
                date_added=kev.get("date_added"),
                due_date=due,
                overdue_days=(today - due).days if due and due < today else None,
            )
        if detail:
            out.enriched = True
            out.description = detail.get("description")
            out.remediation = detail.get("remediation")
            out.weaknesses = list(detail.get("weaknesses") or [])
            out.pocs = [PocRef(**p) for p in (detail.get("pocs") or []) if p.get("url")]
            out.poc_count = int(detail.get("poc_count") or 0)
            out.poc_first_seen = detail.get("poc_first_seen")
            out.template_available = detail.get("template_available")
            out.is_remote = detail.get("is_remote")
            out.needs_auth = detail.get("needs_auth")
            out.patch_available = detail.get("patch_available")
            out.vendor_kev = bool(detail.get("vendor_kev"))
            out.exposure_hosts = detail.get("exposure_hosts")
            out.exposure_products = [
                ExposureProduct(**p) for p in (detail.get("exposure_products") or [])
            ]
            out.hackerone_rank = detail.get("hackerone_rank")
            out.hackerone_reports = detail.get("hackerone_reports")
            out.published_at = detail.get("published_at")
            out.fetched_at = detail.get("fetched_at")
        return out

    async def finding(self, vulnerability_id: uuid.UUID) -> FindingIntel:
        row = (
            await self.session.execute(
                text(
                    "SELECT exploit_score, cve_ids::jsonb AS cve_ids, intel_at"
                    " FROM vulnerabilities WHERE id = :id"
                ),
                {"id": vulnerability_id},
            )
        ).first()
        if row is None:
            return FindingIntel()
        signals = [
            SignalRead(
                kind=s.kind,
                label=SIGNALS_BY_KIND[s.kind].label,
                help=SIGNALS_BY_KIND[s.kind].help,
                tone=SIGNALS_BY_KIND[s.kind].tone,
                weight=s.weight,
                reason=s.reason,
                evidence=s.evidence or {},
            )
            for s in await self.session.execute(
                text(
                    "SELECT kind, weight, reason, evidence FROM intel_signals"
                    " WHERE vulnerability_id = :id ORDER BY weight DESC"
                ),
                {"id": vulnerability_id},
            )
            if s.kind in SIGNALS_BY_KIND
        ]
        cves = [await self.cve(c) for c in (row.cve_ids or [])[:6]]
        stale = (
            row.intel_at is None or (utc_now() - row.intel_at).days > STALE_INTEL_DAYS
        )
        return FindingIntel(
            exploit_score=int(row.exploit_score or 0),
            signals=signals,
            cves=cves,
            stale=stale,
        )
