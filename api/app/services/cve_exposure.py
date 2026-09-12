"""One CVE across both findings dimensions, counted on the evidence ladder."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import cast, func, not_, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services.asset_query import (
    NO_JIT,
    QueryScope,
    vuln_corroborated_ids,
    vuln_evidence,
    vuln_suppressed,
)
from app.services.surface_scope import SurfaceScopeService
from shared.definitions.evidence import (
    EVIDENCE_HELP,
    EVIDENCE_LABELS,
    EVIDENCE_ORDER,
    EVIDENCE_RANK,
    Evidence,
    evidence_rank,
)
from shared.definitions.software import CAVEAT_LABELS
from shared.definitions.surface import SurfaceDimension
from shared.definitions.threat_intel import exploit_band
from shared.definitions.vulnerabilities import (
    SEVERITY_RANK,
    SUPPRESSED_STATES,
    VulnState,
)
from shared.models.cve_exposure import (
    CveExposure,
    CveIndex,
    CveIndexRow,
    CveLadderStep,
    CveLocation,
    CveTargetRow,
)
from shared.models.software import NvdCpeMatch, NvdCve, SoftwareCve
from shared.models.target import Target
from shared.models.threat_intel import EpssScore, KevEntry
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage
from shared.utils.datetime import utc_now

MAX_LOCATIONS = 500
MAX_INDEX_ROWS = 200
DEFAULT_PAGE_SIZE = 50

_AGG = """
WITH sw AS (
    SELECT cve, target_id, coalesce(host, ip) AS asset, discovered_at, severity,
           cvss_score, epss_score, is_kev, kev_ransomware, exploit_score, evidence
      FROM software_cves
     WHERE scan_id = ANY(:software_scans)
), vu AS (
    SELECT c.value AS cve, v.target_id, coalesce(v.host, v.ip) AS asset, v.discovered_at,
           v.severity, v.cvss_score, v.epss_score, v.is_kev, v.kev_ransomware,
           v.exploit_score, v.evidence
      FROM vulnerabilities v, jsonb_array_elements_text(v.cve_ids::jsonb) c
     WHERE v.scan_id = ANY(:finding_scans)
       AND NOT EXISTS (
           SELECT 1 FROM vulnerability_triage t
            WHERE t.target_id = v.target_id AND t.fingerprint = v.fingerprint
              AND t.state = ANY(:suppressed))
), rows AS (
    SELECT 's' AS src, * FROM sw
    UNION ALL
    SELECT 'v' AS src, * FROM vu
), agg AS (
    SELECT r.cve,
           count(DISTINCT r.asset) AS assets,
           count(DISTINCT r.target_id) AS targets,
           count(*) FILTER (WHERE r.src = 's') AS software,
           count(*) FILTER (WHERE r.src = 'v') AS findings,
           bool_or(r.is_kev) AS is_kev,
           bool_or(r.kev_ransomware) AS kev_ransomware,
           max(r.exploit_score) AS exploit_score,
           max(r.cvss_score) AS cvss_score,
           max(r.epss_score) AS epss_score,
           min(r.discovered_at) AS first_seen,
           coalesce(max(n.severity), min({sev_rank})) AS severity,
           max({ev_rank}) AS top_evidence
      FROM rows r
      LEFT JOIN nvd_cves n ON n.cve = r.cve
     WHERE (:needle = '' OR r.cve ILIKE :needle)
     GROUP BY r.cve
)
"""

_SORTS: dict[str, str] = {
    "rank": "is_kev {dir}, exploit_score {dir}, cvss_score {dir} NULLS LAST, assets {dir}",
    "cve": "cve {dir}",
    "severity": "severity_rank {adir}, cvss_score {dir} NULLS LAST",
    "cvss": "cvss_score {dir} NULLS LAST",
    "epss": "epss_score {dir} NULLS LAST",
    "assets": "assets {dir}",
    "targets": "targets {dir}",
    "first_seen": "first_seen {dir} NULLS LAST",
}

_FILTERS: dict[str, str] = {
    "kev": "is_kev",
    "ransomware": "kev_ransomware",
}

_INDEX_TOTAL = """
SELECT count(DISTINCT cve) FROM (
    SELECT cve FROM software_cves WHERE scan_id = ANY(:software_scans)
    UNION ALL
    SELECT c.value FROM vulnerabilities v, jsonb_array_elements_text(v.cve_ids::jsonb) c
     WHERE v.scan_id = ANY(:finding_scans)
       AND NOT EXISTS (
           SELECT 1 FROM vulnerability_triage t
            WHERE t.target_id = v.target_id AND t.fingerprint = v.fingerprint
              AND t.state = ANY(:suppressed))
) x WHERE (:needle = '' OR cve ILIKE :needle)
"""


def _case(ranks: dict[str, int], column: str) -> str:
    arms = " ".join(f"WHEN '{k}' THEN {v}" for k, v in ranks.items())
    return f"(CASE {column} {arms} ELSE {len(ranks)} END)"


def _label(ranks: dict[str, int], expr: str) -> str:
    arms = " ".join(f"WHEN {v} THEN '{k}'" for k, v in ranks.items())
    return f"(CASE {expr} {arms} ELSE NULL END)"


_SEV_RANK = _case(SEVERITY_RANK, "r.severity")
_AGG_SQL = _AGG.format(
    sev_rank=_label(SEVERITY_RANK, _SEV_RANK),
    ev_rank=_label(EVIDENCE_RANK, _case(EVIDENCE_RANK, "r.evidence")),
)


class CveExposureService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.scopes = SurfaceScopeService(session)

    async def _scopes(self, project_id: UUID) -> tuple[QueryScope, QueryScope]:
        software = await self.scopes.scope(project_id, SurfaceDimension.SOFTWARE.value)
        findings = await self.scopes.scope(
            project_id, SurfaceDimension.VULNERABILITIES.value
        )
        return software, findings

    async def _corpus_ready(self) -> bool:
        return bool(await self.session.scalar(select(NvdCpeMatch.cve).limit(1)))

    def _params(
        self, software: QueryScope, findings: QueryScope, q: str = ""
    ) -> dict[str, object]:
        return {
            "software_scans": [str(i) for i in software.ids],
            "finding_scans": [str(i) for i in findings.ids],
            "suppressed": list(SUPPRESSED_STATES),
            "needle": f"%{q.strip()}%" if q.strip() else "",
        }

    async def total(self, project_id: UUID, q: str = "") -> int:
        software, findings = await self._scopes(project_id)
        if not software and not findings:
            return 0
        await self.session.execute(text(NO_JIT))
        counted = await self.session.scalar(
            text(_INDEX_TOTAL), self._params(software, findings, q)
        )
        return int(counted or 0)

    async def index(
        self,
        project_id: UUID,
        q: str = "",
        *,
        page: int = 1,
        size: int = DEFAULT_PAGE_SIZE,
        sort: str = "rank",
        direction: str = "desc",
        severity: str | None = None,
        kev: bool = False,
        ransomware: bool = False,
        evidence: Sequence[str] = (),
    ) -> CveIndex:
        software, findings = await self._scopes(project_id)
        size = max(1, min(size, MAX_INDEX_ROWS))
        page = max(1, page)
        params = self._params(software, findings, q)
        rungs = [e for e in evidence if e in EVIDENCE_RANK]

        where: list[str] = []
        if kev:
            where.append(_FILTERS["kev"])
        if ransomware:
            where.append(_FILTERS["ransomware"])
        if rungs:
            where.append("top_evidence = ANY(:evidence)")
            params["evidence"] = rungs
        facet_where = " AND ".join(where) or "true"
        if severity in SEVERITY_RANK:
            where.append("severity = :severity")
            params["severity"] = severity
        row_where = " AND ".join(where) or "true"

        desc = direction.lower() != "asc"
        order = _SORTS.get(sort, _SORTS["rank"]).format(
            dir="DESC" if desc else "ASC", adir="ASC" if desc else "DESC"
        )
        rank = _case(SEVERITY_RANK, "severity")

        await self.session.execute(text(NO_JIT))
        rows = (
            await self.session.execute(
                text(
                    f"{_AGG_SQL}\nSELECT *, {rank} AS severity_rank, count(*) OVER () AS matched"
                    f"\n  FROM agg WHERE {row_where}"
                    f"\n ORDER BY {order}, cve LIMIT :size OFFSET :offset"
                ),
                {**params, "size": size, "offset": (page - 1) * size},
            )
        ).all()
        facets = (
            await self.session.execute(
                text(
                    f"{_AGG_SQL}\nSELECT severity, count(*) AS n"
                    f"\n  FROM agg WHERE {facet_where} GROUP BY severity"
                ),
                params,
            )
        ).all()

        counts = dict.fromkeys(SEVERITY_RANK, 0)
        for row in facets:
            if row.severity in counts:
                counts[row.severity] = int(row.n or 0)
        return CveIndex(
            items=[
                CveIndexRow(
                    cve=r.cve,
                    severity=r.severity,
                    cvss_score=r.cvss_score,
                    epss_score=r.epss_score,
                    is_kev=bool(r.is_kev),
                    kev_ransomware=bool(r.kev_ransomware),
                    exploit_score=int(r.exploit_score or 0),
                    assets=int(r.assets or 0),
                    targets=int(r.targets or 0),
                    software=int(r.software or 0),
                    findings=int(r.findings or 0),
                    top_evidence=r.top_evidence or Evidence.INFERRED.value,
                    first_seen=r.first_seen,
                )
                for r in rows
            ],
            total=int(rows[0].matched) if rows else 0,
            page=page,
            size=size,
            severity_counts=counts,
            matched=sum(counts.values()),
            software_scans=len(software.ids),
            finding_scans=len(findings.ids),
            corpus_ready=await self._corpus_ready(),
            generated_at=utc_now(),
        )

    async def exposure(self, project_id: UUID, cve: str) -> CveExposure:
        software, findings = await self._scopes(project_id)
        out = CveExposure(
            cve=cve,
            software_scans=len(software.ids),
            finding_scans=len(findings.ids),
            corpus_ready=await self._corpus_ready(),
            generated_at=utc_now(),
        )
        await self._intel(out)
        await self.session.execute(text(NO_JIT))
        await self._rank(out, software, findings)

        software_rows = await self._software_rows(software, cve)
        finding_rows, suppressed = await self._finding_rows(findings, cve)
        out.suppressed = suppressed
        out.ladder = await self._ladder(software, findings, cve)
        out.software_rows = sum(step.software for step in out.ladder)
        out.finding_rows = sum(step.findings for step in out.ladder)

        locations = software_rows + finding_rows
        locations.sort(
            key=lambda x: (
                -evidence_rank(x.evidence),
                x.host or x.ip or "",
                x.port or 0,
            )
        )
        names = await self._targets(project_id)
        for loc in locations:
            loc.target_value = names.get(loc.target_id, (None, None))[0]
        out.locations_total = len(locations)
        out.locations = locations[:MAX_LOCATIONS]
        out.assets = len({loc.host or loc.ip or "" for loc in locations})
        out.first_seen = min((loc.discovered_at for loc in locations), default=None)
        out.by_target = self._by_target(locations, names)
        out.targets = len(out.by_target)
        return out

    async def _intel(self, out: CveExposure) -> None:
        nvd = await self.session.get(NvdCve, out.cve)
        if nvd is not None:
            out.known = True
            out.severity = nvd.severity
            out.cvss_score = nvd.cvss_score
            out.cvss_vector = nvd.cvss_vector
            out.description = nvd.description
            out.published_at = nvd.published_at
            out.last_modified_at = nvd.last_modified_at
        epss = await self.session.get(EpssScore, out.cve)
        if epss is not None:
            out.epss_score = epss.score
            out.epss_percentile = epss.percentile
            out.band = exploit_band(epss.score)
        kev = await self.session.get(KevEntry, out.cve)
        if kev is not None:
            out.is_kev = True
            out.kev_ransomware = bool(kev.known_ransomware)
            out.kev_date_added = kev.date_added
            out.kev_due_date = kev.due_date
            out.kev_required_action = kev.required_action

    async def _rank(
        self, out: CveExposure, software: QueryScope, findings: QueryScope
    ) -> None:
        """The exploitation rank the feeds gave this CVE on the rows that carry it."""
        best: tuple[int, list[str]] = (0, [])
        if software.ids:
            row = (
                await self.session.execute(
                    select(SoftwareCve.exploit_score, SoftwareCve.intel_kinds)
                    .where(
                        software.match(SoftwareCve.scan_id), SoftwareCve.cve == out.cve
                    )
                    .order_by(SoftwareCve.exploit_score.desc())
                    .limit(1)
                )
            ).first()
            if row and int(row[0] or 0) >= best[0]:
                best = (int(row[0] or 0), list(row[1] or []))
        if findings.ids:
            row = (
                await self.session.execute(
                    select(Vulnerability.exploit_score, Vulnerability.intel_kinds)
                    .where(
                        findings.match(Vulnerability.scan_id),
                        func.jsonb_exists(cast(Vulnerability.cve_ids, JSONB), out.cve),
                    )
                    .order_by(Vulnerability.exploit_score.desc())
                    .limit(1)
                )
            ).first()
            if row and int(row[0] or 0) > best[0]:
                best = (int(row[0] or 0), list(row[1] or []))
        out.exploit_score, out.intel_kinds = best

    async def _ladder(
        self, software: QueryScope, findings: QueryScope, cve: str
    ) -> list[CveLadderStep]:
        by_software: dict[str, int] = {}
        if software.ids:
            rows = await self.session.execute(
                select(SoftwareCve.evidence, func.count())
                .where(software.match(SoftwareCve.scan_id), SoftwareCve.cve == cve)
                .group_by(SoftwareCve.evidence)
            )
            by_software = {k: int(n) for k, n in rows.all()}
        by_finding: dict[str, int] = {}
        if findings.ids:
            named = func.jsonb_exists(cast(Vulnerability.cve_ids, JSONB), cve)
            counts = [
                func.count().filter(vuln_evidence(findings, step)).label(step)
                for step in EVIDENCE_ORDER
                if step != Evidence.INFERRED.value
            ]
            row = (
                await self.session.execute(
                    select(*counts).where(
                        findings.match(Vulnerability.scan_id),
                        named,
                        not_(vuln_suppressed(findings)),
                    )
                )
            ).one()
            by_finding = {step: int(row._mapping[step] or 0) for step in row._mapping}
        return [
            CveLadderStep(
                evidence=step,
                label=EVIDENCE_LABELS[step],
                help=EVIDENCE_HELP[step],
                software=by_software.get(step, 0),
                findings=by_finding.get(step, 0),
                count=by_software.get(step, 0) + by_finding.get(step, 0),
            )
            for step in EVIDENCE_ORDER
        ]

    async def _software_rows(self, scope: QueryScope, cve: str) -> list[CveLocation]:
        if not scope.ids:
            return []
        rows = (
            (
                await self.session.execute(
                    select(SoftwareCve)
                    .where(scope.match(SoftwareCve.scan_id), SoftwareCve.cve == cve)
                    .order_by(SoftwareCve.host, SoftwareCve.ip, SoftwareCve.port)
                    .limit(MAX_LOCATIONS * 2)
                )
            )
            .scalars()
            .all()
        )
        return [
            CveLocation(
                dimension=SurfaceDimension.SOFTWARE.value,
                id=r.id,
                scan_id=r.scan_id,
                target_id=r.target_id,
                host=r.host,
                ip=r.ip,
                port=r.port,
                url=r.url,
                evidence=r.evidence,
                evidence_label=EVIDENCE_LABELS.get(r.evidence, ""),
                basis=f"{r.name} {r.version}",
                detail=r.cpe,
                severity=r.severity,
                confidence=r.confidence,
                caveats=[CAVEAT_LABELS.get(c, c) for c in (r.caveats or [])],
                discovered_at=r.discovered_at,
            )
            for r in rows
        ]

    async def _finding_rows(
        self, scope: QueryScope, cve: str
    ) -> tuple[list[CveLocation], int]:
        if not scope.ids:
            return [], 0
        named = func.jsonb_exists(cast(Vulnerability.cve_ids, JSONB), cve)
        suppressed = int(
            await self.session.scalar(
                select(func.count()).where(
                    scope.match(Vulnerability.scan_id), named, vuln_suppressed(scope)
                )
            )
            or 0
        )
        corroborated = vuln_corroborated_ids(scope).subquery("cve_corroborated")
        triage = aliased(VulnerabilityTriage)
        rows = (
            await self.session.execute(
                select(
                    Vulnerability,
                    corroborated.c.id.isnot(None).label("agreed"),
                    triage.state,
                )
                .outerjoin(corroborated, corroborated.c.id == Vulnerability.id)
                .outerjoin(
                    triage,
                    (triage.target_id == Vulnerability.target_id)
                    & (triage.fingerprint == Vulnerability.fingerprint),
                )
                .where(
                    scope.match(Vulnerability.scan_id),
                    named,
                    not_(vuln_suppressed(scope)),
                )
                .order_by(Vulnerability.host, Vulnerability.matched_at)
                .limit(MAX_LOCATIONS * 2)
            )
        ).all()
        out = []
        for v, agreed, state in rows:
            if v.evidence == Evidence.PROVEN.value:
                evidence = Evidence.PROVEN.value
            elif agreed:
                evidence = Evidence.CORROBORATED.value
            else:
                evidence = Evidence.OBSERVED.value
            out.append(
                CveLocation(
                    dimension=SurfaceDimension.VULNERABILITIES.value,
                    id=v.id,
                    scan_id=v.scan_id,
                    target_id=v.target_id,
                    host=v.host,
                    ip=v.ip,
                    port=v.port,
                    url=v.matched_at,
                    evidence=evidence,
                    evidence_label=EVIDENCE_LABELS[evidence],
                    basis=v.template_name,
                    detail=v.template_id,
                    severity=v.severity,
                    state=state or VulnState.OPEN.value,
                    discovered_at=v.discovered_at,
                )
            )
        return out, suppressed

    async def _targets(self, project_id: UUID) -> dict[UUID, tuple[str, str]]:
        rows = await self.session.execute(
            select(Target.id, Target.target_value, Target.target_type).where(
                Target.project_id == project_id
            )
        )
        return {
            row[0]: (row[1], str(getattr(row[2], "value", row[2]) or ""))
            for row in rows.all()
        }

    @staticmethod
    def _by_target(
        locations: list[CveLocation], names: dict[UUID, tuple[str, str]]
    ) -> list[CveTargetRow]:
        grouped: dict[UUID, CveTargetRow] = {}
        assets: dict[UUID, set[str]] = {}
        for loc in locations:
            value, kind = names.get(loc.target_id, ("", ""))
            row = grouped.setdefault(
                loc.target_id,
                CveTargetRow(
                    target_id=loc.target_id, target_value=value, target_type=kind
                ),
            )
            assets.setdefault(loc.target_id, set()).add(loc.host or loc.ip or "")
            if loc.dimension == SurfaceDimension.SOFTWARE.value:
                row.software += 1
            else:
                row.findings += 1
            if row.first_seen is None or loc.discovered_at < row.first_seen:
                row.first_seen = loc.discovered_at
        for target_id, row in grouped.items():
            row.assets = len(assets[target_id])
        return sorted(
            grouped.values(), key=lambda r: (-r.assets, -r.findings, r.target_value)
        )
