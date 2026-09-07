"""Read side of the exploitation intelligence: feed state, coverage, per-CVE detail."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.threat_intel import (
    BANDS_BY_KEY,
    FEED_STATUS_LABELS,
    FEEDS,
    SIGNALS_BY_KIND,
    FeedStatus,
    exploit_band,
)
from shared.models.threat_intel import (
    CveIntelRead,
    ExposureProduct,
    FindingIntel,
    IntelChange,
    IntelCoverage,
    KevDetail,
    PocRef,
    SignalFinding,
    SignalRead,
    ThreatFeedRead,
    ThreatIntelStatus,
)
from shared.services.threat_intel import feed_age_hours, feed_status
from shared.utils.datetime import utc_now

_COVERAGE_SQL = """
SELECT count(*)                                                              AS findings,
       count(*) FILTER (WHERE jsonb_array_length(cve_ids::jsonb) > 0)        AS with_cve,
       count(*) FILTER (WHERE epss_score IS NOT NULL)                        AS scored,
       count(*) FILTER (WHERE is_kev)                                        AS kev,
       count(*) FILTER (WHERE kev_ransomware)                                AS ransomware,
       count(*) FILTER (WHERE kev_due_date IS NOT NULL
                          AND kev_due_date < current_date)                   AS overdue,
       count(*) FILTER (WHERE coalesce(poc_count, 0) > 0)                    AS weaponised,
       count(*) FILTER (WHERE template_available IS FALSE)                   AS untestable,
       count(*) FILTER (WHERE intel_at IS NOT NULL)                          AS enriched,
       max(intel_at)                                                         AS last_applied_at
FROM vulnerabilities
{scope}
"""

_BANDS_SQL = """
SELECT CASE
         WHEN epss_score >= 0.5   THEN 'very_likely'
         WHEN epss_score >= 0.088 THEN 'likely'
         WHEN epss_score >= 0.01  THEN 'possible'
         ELSE 'unlikely'
       END AS band,
       count(*) AS n
FROM vulnerabilities
WHERE epss_score IS NOT NULL {and_scope}
GROUP BY 1
"""

# a signal's own created_at is when the finding first earned it, so this is a real delta
_SIGNAL_FINDINGS_SQL = """
SELECT DISTINCT ON (v.id)
       v.id, v.scan_id, v.target_id, v.template_name, v.severity, v.host, v.matched_at,
       v.epss_score, v.exploit_score, v.cve_ids::jsonb AS cve_ids,
       s.reason, s.created_at, t.target_value
FROM intel_signals s
JOIN vulnerabilities v ON v.id = s.vulnerability_id
JOIN targets t ON t.id = v.target_id
WHERE s.kind = ANY(:kinds) {and_scope}
ORDER BY v.id, v.exploit_score DESC, v.epss_score DESC NULLS LAST
LIMIT :limit
"""

STALE_INTEL_DAYS = 2

_CHANGES_SQL = """
SELECT s.vulnerability_id, s.kind, s.created_at, s.reason,
       v.scan_id, v.target_id, v.template_name, v.severity, v.host, v.matched_at,
       v.epss_score, v.cve_ids::jsonb AS cve_ids, t.target_value
FROM intel_signals s
JOIN vulnerabilities v ON v.id = s.vulnerability_id
JOIN targets t ON t.id = v.target_id
WHERE s.kind = ANY(:kinds)
  AND s.created_at > now() - make_interval(days => :days)
  {and_scope}
ORDER BY s.created_at DESC
LIMIT :limit
"""


class ThreatIntelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _scope(self, project_id: uuid.UUID | None) -> tuple[str, dict]:
        if project_id is None:
            return "", {}
        return "WHERE project_id = :project_id", {"project_id": project_id}

    async def coverage(self, project_id: uuid.UUID | None = None) -> IntelCoverage:
        scope, params = await self._scope(project_id)
        row = (
            await self.session.execute(text(_COVERAGE_SQL.format(scope=scope)), params)
        ).one()
        and_scope = "AND project_id = :project_id" if project_id else ""
        bands = {
            r.band: int(r.n)
            for r in await self.session.execute(
                text(_BANDS_SQL.format(and_scope=and_scope)), params
            )
        }
        return IntelCoverage(
            findings=int(row.findings or 0),
            with_cve=int(row.with_cve or 0),
            scored=int(row.scored or 0),
            kev=int(row.kev or 0),
            ransomware=int(row.ransomware or 0),
            overdue=int(row.overdue or 0),
            weaponised=int(row.weaponised or 0),
            untestable=int(row.untestable or 0),
            enriched=int(row.enriched or 0),
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
        counts = dict(
            (
                await self.session.execute(
                    text(
                        "SELECT 'epss' AS k, count(*) AS n FROM epss_scores"
                        " UNION ALL SELECT 'kev', count(*) FROM kev_entries"
                    )
                )
            ).all()
        )
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
                    status=status,
                    status_label=FEED_STATUS_LABELS.get(status, status),
                    rows=int(counts.get(spec.kind, 0)),
                    version=row.version if row else None,
                    bytes=int(row.bytes) if row else 0,
                    duration_ms=int(row.duration_ms) if row else 0,
                    error=row.error if row else None,
                    last_synced_at=row.last_synced_at if row else None,
                    age_hours=feed_age_hours(row),
                )
            )
        return out

    async def changes(
        self, project_id: uuid.UUID | None, *, days: int = 7, limit: int = 20
    ) -> list[IntelChange]:
        and_scope = "AND v.project_id = :project_id" if project_id else ""
        params: dict = {
            "kinds": ["kev", "ransom_path", "fresh_exploit", "weaponised"],
            "days": days,
            "limit": limit,
        }
        if project_id:
            params["project_id"] = project_id
        rows = await self.session.execute(
            text(_CHANGES_SQL.format(and_scope=and_scope)), params
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
        self, kind: str, project_id: uuid.UUID | None, *, limit: int = 100
    ) -> list[SignalFinding]:
        """`kind` may name several signals, so a tile counting a column can open all of them."""
        kinds = [k.strip() for k in kind.split(",") if k.strip()]
        and_scope = "AND v.project_id = :project_id" if project_id else ""
        params: dict = {"kinds": kinds, "limit": limit}
        if project_id:
            params["project_id"] = project_id
        rows = await self.session.execute(
            text(_SIGNAL_FINDINGS_SQL.format(and_scope=and_scope)), params
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
                reason=r.reason,
            )
            for r in rows
        ]

    async def status(self, project_id: uuid.UUID | None = None) -> ThreatIntelStatus:
        feeds = await self.feeds()
        coverage = await self.coverage(project_id)
        cached = int(
            (
                await self.session.execute(text("SELECT count(*) FROM cve_intel"))
            ).scalar()
            or 0
        )
        has_key = bool(
            (
                await self.session.execute(
                    text(
                        "SELECT 1 FROM api_keys WHERE provider = 'VULNX'"
                        " AND is_enabled LIMIT 1"
                    )
                )
            ).scalar()
        )
        last_applied = (
            await self.session.execute(
                text("SELECT max(intel_at) FROM vulnerabilities")
            )
        ).scalar()
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
            provider_enabled=cached > 0 or has_key,
            provider_cached=cached,
            last_applied_at=last_applied,
            recent_changes=await self.changes(project_id),
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
