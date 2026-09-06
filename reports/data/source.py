"""Everything a report can know, gathered once and cached. Counts come from the tables."""

from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, distinct, func, select, text
from sqlalchemy.orm import Session, aliased

from reports.data.models import (
    Address,
    Certificate,
    DimensionCoverage,
    EndpointRow,
    Facet,
    Finding,
    Host,
    Service,
    StageRun,
)
from shared.definitions.ports import SENSITIVE_PORTS, ServiceClass
from shared.definitions.reports import MAX_REPORT_ROWS, ReportScope
from shared.definitions.surface import SURFACE_KINDS, SURFACE_ORDER, SurfaceDimension
from shared.definitions.vulnerabilities import (
    SUPPRESSED_STATES,
    Severity,
    severity_rank,
)
from shared.enums.scan import ScanStatus
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.vulnerability import (
    Vulnerability,
    VulnerabilityCoverage,
    VulnerabilityTriage,
)
from shared.utils.datetime import utc_now

_DIM = SurfaceDimension
_MAX_HOSTS_PER_IP = 6
_SERVER_ERROR = 500
_TABLE = {
    _DIM.WEB_ASSETS.value: Subdomain,
    _DIM.IPS.value: IpAddress,
    _DIM.SERVICES.value: Port,
    _DIM.ENDPOINTS.value: Endpoint,
    _DIM.VULNERABILITIES.value: Vulnerability,
}
_KEY = {
    _DIM.WEB_ASSETS.value: (Subdomain.name,),
    _DIM.IPS.value: (IpAddress.ip,),
    _DIM.SERVICES.value: (Port.ip, Port.number, Port.protocol),
    _DIM.ENDPOINTS.value: (Endpoint.signature,),
    _DIM.VULNERABILITIES.value: (Vulnerability.fingerprint,),
}
# the column a person reads, which is not always the column that identifies the row
_LABEL = {
    _DIM.WEB_ASSETS.value: Subdomain.name,
    _DIM.IPS.value: IpAddress.ip,
    _DIM.SERVICES.value: Port.ip,
    _DIM.ENDPOINTS.value: Endpoint.url,
    _DIM.VULNERABILITIES.value: Vulnerability.matched_at,
}


class ReportSource:
    """Reads for one scan, or for a target's most recent covering run per dimension."""

    def __init__(
        self,
        session: Session,
        *,
        scope: str,
        scan: Scan | None,
        target: Target,
        project_name: str = "",
    ) -> None:
        self.session = session
        self.scope = scope
        self.scan = scan
        self.target = target
        self.project_name = project_name
        self._memo: dict[str, Any] = {}

    # ---------- identity ----------

    @property
    def subject(self) -> str:
        return self.target.target_value

    @property
    def subject_type(self) -> str:
        value = self.target.target_type
        return getattr(value, "value", str(value)).lower()

    @property
    def is_scan_scope(self) -> bool:
        return self.scope == ReportScope.SCAN.value

    @cached_property
    def observed_at(self) -> datetime | None:
        if self.scan is not None:
            return (
                self.scan.completed_at or self.scan.started_at or self.scan.created_at
            )
        stamps = [c.observed_at for c in self.coverage.values() if c.observed_at]
        return max(stamps) if stamps else None

    @property
    def observed_label(self) -> str:
        return self.observed_at.strftime("%d %b %Y") if self.observed_at else "—"

    # ---------- scan selection ----------

    @cached_property
    def runs(self) -> list[Scan]:
        rows = (
            self.session.execute(
                select(Scan)
                .where(Scan.target_id == self.target.id)
                .order_by(Scan.created_at.desc())
                .limit(60)
            )
            .scalars()
            .all()
        )
        return list(rows)

    def scan_for(self, dimension: str) -> UUID | None:
        """The run whose rows this dimension is reported from."""
        if self.is_scan_scope:
            return self.scan.id if self.scan else None
        key = f"scan_for:{dimension}"
        if key in self._memo:
            return self._memo[key]
        table = _TABLE[dimension]
        row = self.session.execute(
            select(table.scan_id, func.max(Scan.created_at).label("at"))
            .join(Scan, Scan.id == table.scan_id)
            .where(table.target_id == self.target.id)
            .group_by(table.scan_id)
            .order_by(func.max(Scan.created_at).desc())
            .limit(1)
        ).first()
        found = row[0] if row else None
        self._memo[key] = found
        return found

    @cached_property
    def previous_scan(self) -> Scan | None:
        if self.scan is None:
            return None
        cutoff = self.scan.started_at or self.scan.created_at
        return (
            self.session.execute(
                select(Scan)
                .where(
                    Scan.target_id == self.target.id,
                    Scan.id != self.scan.id,
                    Scan.created_at < cutoff,
                    Scan.status == ScanStatus.COMPLETED.value,
                )
                .order_by(Scan.created_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )

    @property
    def cutoff(self) -> datetime | None:
        if self.scan is not None:
            return self.scan.started_at or self.scan.created_at
        return self.observed_at

    # ---------- coverage ----------

    @cached_property
    def planned_stages(self) -> dict[str, dict]:
        if self.scan is None:
            return {}
        config = self.scan.execution_config or {}
        return {
            name: values
            for name, values in (config.get("stages") or {}).items()
            if (values or {}).get("enabled", True)
        }

    @cached_property
    def producing_stages(self) -> dict[str, set[str]]:
        """Dimension -> the enabled stages that produce it."""
        try:
            from stages.registry import stages as stage_specs  # noqa: PLC0415
        except ImportError:
            return {}
        specs = {spec.name: spec for spec in stage_specs()}
        out: dict[str, set[str]] = {dim: set() for dim in SURFACE_ORDER}
        for name in self.planned_stages:
            spec = specs.get(name)
            if spec is None:
                continue
            for dimension, kinds in SURFACE_KINDS.items():
                if spec.produces & kinds:
                    out[dimension].add(name)
        return out

    def _count(self, dimension: str, scan_id: UUID | None) -> int:
        if scan_id is None:
            return 0
        table = _TABLE[dimension]
        query = select(func.count()).select_from(table).where(table.scan_id == scan_id)
        if dimension == _DIM.VULNERABILITIES.value:
            query = query.where(self._not_suppressed())
        return int(self.session.execute(query).scalar() or 0)

    @cached_property
    def coverage(self) -> dict[str, DimensionCoverage]:
        out: dict[str, DimensionCoverage] = {}
        for dimension in SURFACE_ORDER:
            scan_id = self.scan_for(dimension)
            count = self._count(dimension, scan_id)
            planned = bool(self.producing_stages.get(dimension))
            covered = count > 0 or (planned and self.scan is not None)
            observed = None
            if scan_id is not None:
                run = next((r for r in self.runs if r.id == scan_id), self.scan)
                if run is not None:
                    observed = run.completed_at or run.started_at or run.created_at
            entry = DimensionCoverage(
                dimension=dimension,
                covered=covered,
                count=count,
                observed_at=observed,
                scan_id=str(scan_id) if scan_id else "",
            )
            if not covered:
                entry.note = "No run has produced this."
            out[dimension] = entry
        self._attach_previous(out)
        return out

    def _attach_previous(self, coverage: dict[str, DimensionCoverage]) -> None:
        previous = self.previous_scan
        if previous is None:
            return
        covered_before = self._covered_by(previous)
        for dimension, entry in coverage.items():
            if not entry.covered or dimension not in covered_before:
                continue
            entry.previous = self._count(dimension, previous.id)

    def _covered_by(self, scan: Scan) -> set[str]:
        """Rows are the only proof a previous run produced a dimension, so only they anchor a delta."""
        return {d for d in SURFACE_ORDER if self._count(d, scan.id)}

    @cached_property
    def covered_dimensions(self) -> frozenset[str]:
        return frozenset(d for d, c in self.coverage.items() if c.covered)

    def count_of(self, dimension: str) -> int:
        return self.coverage[dimension].count

    # ---------- baselines ----------

    def _baseline_keys(self, dimension: str) -> set[tuple]:
        key = f"baseline:{dimension}"
        if key in self._memo:
            return self._memo[key]
        table = _TABLE[dimension]
        columns = _KEY[dimension]
        cutoff = self.cutoff
        found: set[tuple] = set()
        if cutoff is not None:
            scan_id = self.scan_for(dimension)
            query = (
                select(*columns)
                .distinct()
                .where(table.target_id == self.target.id, table.discovered_at < cutoff)
            )
            if scan_id is not None:
                query = query.where(table.scan_id != scan_id)
            found = {tuple(row) for row in self.session.execute(query)}
        self._memo[key] = found
        return found

    def has_baseline(self, dimension: str) -> bool:
        return bool(self._baseline_keys(dimension))

    # ---------- vulnerabilities ----------

    @staticmethod
    def _not_suppressed():
        suppressed = (
            select(VulnerabilityTriage.id)
            .where(
                VulnerabilityTriage.target_id == Vulnerability.target_id,
                VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
                VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
            )
            .exists()
        )
        return ~suppressed

    @cached_property
    def triage(self) -> dict[str, tuple[str, str | None]]:
        rows = self.session.execute(
            select(
                VulnerabilityTriage.fingerprint,
                VulnerabilityTriage.state,
                VulnerabilityTriage.note,
            ).where(VulnerabilityTriage.target_id == self.target.id)
        ).all()
        return {row[0]: (row[1], row[2]) for row in rows}

    @cached_property
    def findings(self) -> list[Finding]:
        scan_id = self.scan_for(_DIM.VULNERABILITIES.value)
        if scan_id is None:
            return []
        rows = (
            self.session.execute(
                select(Vulnerability)
                .where(Vulnerability.scan_id == scan_id)
                .limit(MAX_REPORT_ROWS)
            )
            .scalars()
            .all()
        )
        baseline = self._baseline_keys(_DIM.VULNERABILITIES.value)
        known = self.has_baseline(_DIM.VULNERABILITIES.value)
        assets = self._asset_context({r.host for r in rows if r.host})
        out: list[Finding] = []
        for row in rows:
            state, note = self.triage.get(row.fingerprint, ("open", None))
            if state in SUPPRESSED_STATES:
                continue
            asset = assets.get(row.host or "")
            out.append(
                Finding(
                    id=str(row.id),
                    fingerprint=row.fingerprint,
                    template_id=row.template_id,
                    name=row.template_name,
                    severity=row.severity,
                    scanner=row.scanner,
                    protocol=row.protocol,
                    matched_at=row.matched_at,
                    host=row.host,
                    ip=row.ip,
                    port=row.port,
                    url=row.url,
                    description=row.description,
                    impact=row.impact,
                    remediation=row.remediation,
                    references=list(row.references or []),
                    tags=list(row.tags or []),
                    cve_ids=list(row.cve_ids or []),
                    cwe_ids=list(row.cwe_ids or []),
                    cvss_score=row.cvss_score,
                    cvss_metrics=row.cvss_metrics,
                    epss_score=row.epss_score,
                    is_kev=row.is_kev,
                    state=state,
                    note=note,
                    is_new=known and (row.fingerprint,) not in baseline,
                    extracted=[str(v) for v in (row.extracted_results or [])],
                    request=row.request,
                    response=row.response,
                    curl=row.curl_command,
                    matcher=row.matcher_name,
                    discovered_at=row.discovered_at,
                    screenshot=asset[0] if asset else None,
                    asset_title=asset[1] if asset else None,
                    asset_status=asset[2] if asset else None,
                    asset_tech=list(asset[3]) if asset else [],
                )
            )
        out.sort(
            key=lambda f: (
                severity_rank(f.severity),
                not f.is_kev,
                -(f.epss_score or 0),
            )
        )
        return out

    def _asset_context(self, hosts: set[str]) -> dict[str, tuple]:
        if not hosts:
            return {}
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return {}
        rows = self.session.execute(
            select(
                Subdomain.name,
                Subdomain.screenshot_path,
                Subdomain.page_title,
                Subdomain.http_status,
                Subdomain.tech,
            ).where(
                Subdomain.scan_id == scan_id, Subdomain.name.in_(list(hosts)[:2000])
            )
        ).all()
        return {row[0]: (row[1], row[2], row[3], row[4] or []) for row in rows}

    @cached_property
    def coverage_rows(self) -> list[VulnerabilityCoverage]:
        scan_id = self.scan_for(_DIM.VULNERABILITIES.value)
        if scan_id is None:
            return []
        return list(
            self.session.execute(
                select(VulnerabilityCoverage)
                .where(VulnerabilityCoverage.scan_id == scan_id)
                .order_by(VulnerabilityCoverage.started_at)
            )
            .scalars()
            .all()
        )

    @cached_property
    def severity_counts(self) -> dict[str, int]:
        counts = dict.fromkeys((s.value for s in Severity), 0)
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    @cached_property
    def suppressed_count(self) -> int:
        scan_id = self.scan_for(_DIM.VULNERABILITIES.value)
        if scan_id is None:
            return 0
        total = int(
            self.session.execute(
                select(func.count())
                .select_from(Vulnerability)
                .where(Vulnerability.scan_id == scan_id)
            ).scalar()
            or 0
        )
        return max(0, total - len(self.findings))

    # ---------- hosts ----------

    @cached_property
    def host_rows(self) -> list[Host]:
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return []
        newest = (
            select(HttpAsset)
            .where(HttpAsset.scan_id == scan_id)
            .distinct(HttpAsset.host)
            .order_by(HttpAsset.host, HttpAsset.discovered_at.desc())
            .subquery()
        )
        asset = aliased(HttpAsset, newest)
        rows = self.session.execute(
            select(Subdomain, asset)
            .outerjoin(asset, newest.c.host == Subdomain.name)
            .where(Subdomain.scan_id == scan_id)
            .order_by(Subdomain.http_status.is_(None), Subdomain.name)
            .limit(MAX_REPORT_ROWS)
        ).all()

        baseline = self._baseline_keys(_DIM.WEB_ASSETS.value)
        known = self.has_baseline(_DIM.WEB_ASSETS.value)
        by_host = self.findings_by_host
        out: list[Host] = []
        for sub, asset in rows:
            worst = by_host.get(sub.name)
            out.append(
                Host(
                    name=sub.name,
                    status=sub.http_status,
                    title=sub.page_title,
                    url=sub.http_url,
                    ips=list(sub.resolved_ips or []),
                    cname=sub.cname,
                    tech=list((asset.tech if asset else None) or sub.tech or []),
                    webserver=sub.webserver,
                    is_cdn=bool(asset.is_cdn if asset else sub.is_cdn),
                    cdn_name=(asset.cdn_name if asset else None) or sub.cdn_name,
                    cdn_type=asset.cdn_type if asset else None,
                    waf=(asset.waf if asset else None) or sub.waf,
                    asn=sub.asn or (asset.asn if asset else None),
                    asn_org=sub.asn_org or (asset.asn_org if asset else None),
                    tls_issuer=(asset.tls_issuer_org or asset.tls_issuer_cn)
                    if asset
                    else None,
                    tls_not_after=(asset.tls_not_after if asset else None)
                    or sub.tls_not_after,
                    tls_expired=(asset.tls_expired if asset else None)
                    if asset
                    else sub.tls_expired,
                    tls_self_signed=sub.tls_self_signed,
                    screenshot=sub.screenshot_path,
                    sources=list(sub.sources or []),
                    is_new=known and (sub.name,) not in baseline,
                    findings=worst[0] if worst else 0,
                    worst=worst[1] if worst else None,
                )
            )
        return out

    @cached_property
    def findings_by_host(self) -> dict[str, tuple[int, str]]:
        out: dict[str, tuple[int, str]] = {}
        for finding in self.findings:
            key = finding.host or ""
            if not key:
                continue
            count, worst = out.get(key, (0, Severity.UNKNOWN.value))
            best = (
                worst
                if severity_rank(worst) <= severity_rank(finding.severity)
                else finding.severity
            )
            out[key] = (count + 1, best)
        return out

    @cached_property
    def live_hosts(self) -> list[Host]:
        return [h for h in self.host_rows if h.status]

    # ---------- addresses ----------

    @cached_property
    def address_rows(self) -> list[Address]:
        scan_id = self.scan_for(_DIM.IPS.value)
        if scan_id is None:
            return []
        rows = (
            self.session.execute(
                select(IpAddress)
                .where(IpAddress.scan_id == scan_id)
                .order_by(IpAddress.ip)
                .limit(MAX_REPORT_ROWS)
            )
            .scalars()
            .all()
        )
        ports = self._ports_per_ip()
        hosts = self._hosts_per_ip()
        baseline = self._baseline_keys(_DIM.IPS.value)
        known = self.has_baseline(_DIM.IPS.value)
        return [
            Address(
                ip=row.ip,
                version=row.version,
                asn=row.asn,
                asn_org=row.asn_org,
                country=row.country,
                prefix=row.prefix,
                is_cdn=row.is_cdn,
                cdn_name=row.cdn_name,
                cdn_type=row.cdn_type,
                scan_policy=row.scan_policy,
                scan_policy_reason=row.scan_policy_reason,
                ptr=list(row.ptr_hostnames or []),
                open_ports=ports.get(row.ip, 0),
                hosts=hosts.get(row.ip, []),
                is_new=known and (row.ip,) not in baseline,
            )
            for row in rows
        ]

    def _ports_per_ip(self) -> dict[str, int]:
        scan_id = self.scan_for(_DIM.SERVICES.value)
        if scan_id is None:
            return {}
        rows = self.session.execute(
            select(Port.ip, func.count())
            .where(Port.scan_id == scan_id)
            .group_by(Port.ip)
        ).all()
        return {row[0]: int(row[1]) for row in rows}

    def _hosts_per_ip(self) -> dict[str, list[str]]:
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return {}
        rows = self.session.execute(
            select(HttpAsset.ip, HttpAsset.host)
            .where(HttpAsset.scan_id == scan_id, HttpAsset.ip.is_not(None))
            .distinct()
            .limit(20000)
        ).all()
        out: dict[str, list[str]] = {}
        for ip, host in rows:
            bucket = out.setdefault(ip, [])
            if len(bucket) < _MAX_HOSTS_PER_IP and host not in bucket:
                bucket.append(host)
        return out

    # ---------- services ----------

    @cached_property
    def service_rows(self) -> list[Service]:
        scan_id = self.scan_for(_DIM.SERVICES.value)
        if scan_id is None:
            return []
        rows = self.session.execute(
            select(Port, IpAddress)
            .outerjoin(
                IpAddress,
                and_(IpAddress.scan_id == Port.scan_id, IpAddress.ip == Port.ip),
            )
            .where(Port.scan_id == scan_id)
            .order_by(Port.ip, Port.number)
            .limit(MAX_REPORT_ROWS)
        ).all()
        hosts = self._hosts_per_ip()
        baseline = self._baseline_keys(_DIM.SERVICES.value)
        known = self.has_baseline(_DIM.SERVICES.value)
        return [
            Service(
                ip=port.ip,
                port=port.number,
                protocol=port.protocol,
                service_name=port.service_name,
                service_class=port.service_class,
                product=port.product,
                version=port.version,
                banner=port.banner,
                is_http=port.is_http,
                tls=port.tls,
                source=port.source,
                sensitive=port.number in SENSITIVE_PORTS,
                hosts=hosts.get(port.ip, []),
                asn_org=address.asn_org if address else None,
                country=address.country if address else None,
                is_new=known and (port.ip, port.number, port.protocol) not in baseline,
            )
            for port, address in rows
        ]

    @cached_property
    def sensitive_services(self) -> list[Service]:
        return [s for s in self.service_rows if s.sensitive]

    # ---------- endpoints ----------

    @cached_property
    def endpoint_rows(self) -> list[EndpointRow]:
        scan_id = self.scan_for(_DIM.ENDPOINTS.value)
        if scan_id is None:
            return []
        rows = (
            self.session.execute(
                select(Endpoint)
                .where(Endpoint.scan_id == scan_id)
                .order_by(Endpoint.host, Endpoint.path)
                .limit(MAX_REPORT_ROWS)
            )
            .scalars()
            .all()
        )
        baseline = self._baseline_keys(_DIM.ENDPOINTS.value)
        known = self.has_baseline(_DIM.ENDPOINTS.value)
        return [
            EndpointRow(
                url=row.url,
                host=row.host,
                path=row.path,
                status=row.status_code,
                endpoint_class=row.endpoint_class,
                content_type=row.content_type,
                length=row.content_length,
                title=row.title,
                params=list(row.params or []),
                interest=list(row.interest or []),
                sources=list(row.sources or []),
                is_probed=row.is_probed,
                is_new=known and (row.signature,) not in baseline,
            )
            for row in rows
        ]

    # ---------- certificates ----------

    @cached_property
    def certificates(self) -> list[Certificate]:
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return []
        rows = self.session.execute(
            select(
                HttpAsset.host,
                HttpAsset.tls_subject_cn,
                HttpAsset.tls_issuer_org,
                HttpAsset.tls_issuer_cn,
                HttpAsset.tls_not_before,
                HttpAsset.tls_not_after,
                HttpAsset.tls_expired,
                HttpAsset.tls_self_signed,
                HttpAsset.tls_sans,
                HttpAsset.tls_version,
            )
            .where(HttpAsset.scan_id == scan_id, HttpAsset.tls_not_after.is_not(None))
            .distinct(HttpAsset.host)
            .order_by(HttpAsset.host, HttpAsset.id)
            .limit(MAX_REPORT_ROWS)
        ).all()
        now = self.observed_at or utc_now()
        out: list[Certificate] = []
        for row in rows:
            expires = row[5]
            days = None
            if expires is not None:
                try:
                    days = (expires - now).days
                except TypeError:
                    days = None
            out.append(
                Certificate(
                    host=row[0],
                    subject=row[1],
                    issuer=row[2] or row[3],
                    not_before=row[4],
                    not_after=expires,
                    expired=row[6],
                    self_signed=row[7],
                    days_left=days,
                    sans=len(row[8] or []),
                    version=row[9],
                )
            )
        return out

    # ---------- rollups ----------

    def _facet(
        self, column, scan_id: UUID | None, table, limit: int = 12
    ) -> list[Facet]:
        if scan_id is None:
            return []
        rows = self.session.execute(
            select(column, func.count())
            .where(table.scan_id == scan_id, column.is_not(None), column != "")
            .group_by(column)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [Facet(name=str(row[0]), count=int(row[1])) for row in rows]

    @cached_property
    def countries(self) -> list[Facet]:
        return self._facet(IpAddress.country, self.scan_for(_DIM.IPS.value), IpAddress)

    @cached_property
    def networks(self) -> list[Facet]:
        return self._facet(IpAddress.asn_org, self.scan_for(_DIM.IPS.value), IpAddress)

    @cached_property
    def webservers(self) -> list[Facet]:
        return self._facet(
            HttpAsset.webserver, self.scan_for(_DIM.WEB_ASSETS.value), HttpAsset
        )

    @cached_property
    def technologies(self) -> list[Facet]:
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return []
        rows = self.session.execute(
            text(
                "SELECT v AS value, count(DISTINCT a.host) AS c "
                "FROM http_assets a, LATERAL jsonb_array_elements_text(cast(a.tech AS jsonb)) v "
                "WHERE a.scan_id = :sid GROUP BY v ORDER BY c DESC, v ASC LIMIT 14"
            ),
            {"sid": str(scan_id)},
        ).all()
        return [Facet(name=str(row[0]), count=int(row[1])) for row in rows]

    @cached_property
    def status_classes(self) -> list[Facet]:
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return []
        bucket = case(
            (Subdomain.http_status.between(200, 299), "2xx"),
            (Subdomain.http_status.between(300, 399), "3xx"),
            (Subdomain.http_status.between(400, 499), "4xx"),
            (Subdomain.http_status >= _SERVER_ERROR, "5xx"),
            else_="none",
        )
        rows = self.session.execute(
            select(bucket, func.count())
            .where(Subdomain.scan_id == scan_id)
            .group_by(bucket)
            .order_by(bucket)
        ).all()
        return [Facet(name=str(row[0]), count=int(row[1])) for row in rows]

    @cached_property
    def service_classes(self) -> list[Facet]:
        scan_id = self.scan_for(_DIM.SERVICES.value)
        if scan_id is None:
            return []
        rows = self.session.execute(
            select(Port.service_class, func.count())
            .where(Port.scan_id == scan_id)
            .group_by(Port.service_class)
            .order_by(func.count().desc())
        ).all()
        order = [c.value for c in ServiceClass]
        facets = [Facet(name=str(row[0]), count=int(row[1])) for row in rows]
        facets.sort(key=lambda f: order.index(f.name) if f.name in order else 99)
        return facets

    @cached_property
    def top_services(self) -> list[Facet]:
        scan_id = self.scan_for(_DIM.SERVICES.value)
        if scan_id is None:
            return []
        rows = self.session.execute(
            select(Port.service_name, func.count())
            .where(Port.scan_id == scan_id, Port.service_name.is_not(None))
            .group_by(Port.service_name)
            .order_by(func.count().desc())
            .limit(12)
        ).all()
        return [Facet(name=str(row[0]), count=int(row[1])) for row in rows]

    @cached_property
    def cdn_split(self) -> tuple[int, int, int]:
        """Edge, cloud, direct, across resolving hosts."""
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return (0, 0, 0)
        rows = self.session.execute(
            select(HttpAsset.cdn_type, func.count(distinct(HttpAsset.host)))
            .where(HttpAsset.scan_id == scan_id)
            .group_by(HttpAsset.cdn_type)
        ).all()
        edge = cloud = direct = 0
        for kind, count in rows:
            if kind in {"cdn", "waf"}:
                edge += int(count)
            elif kind == "cloud":
                cloud += int(count)
            else:
                direct += int(count)
        return (edge, cloud, direct)

    # ---------- run detail ----------

    @cached_property
    def stage_runs(self) -> list[StageRun]:
        if self.scan is None:
            return []
        rows = (
            self.session.execute(
                select(ScanActivity)
                .where(ScanActivity.scan_id == self.scan.id)
                .order_by(ScanActivity.created_at)
            )
            .scalars()
            .all()
        )
        try:
            from stages.registry import stages as stage_specs  # noqa: PLC0415

            specs = {spec.name: spec for spec in stage_specs()}
        except ImportError:
            specs = {}
        out: list[StageRun] = []
        for row in rows:
            name = getattr(row, "stage_name", None) or getattr(row, "name", "")
            spec = specs.get(name)
            started = getattr(row, "started_at", None) or row.created_at
            ended = getattr(row, "completed_at", None) or getattr(row, "ended_at", None)
            duration = None
            if started and ended:
                duration = (ended - started).total_seconds()
            out.append(
                StageRun(
                    name=name,
                    title=spec.title if spec else name.replace("_", " ").title(),
                    status=str(getattr(row, "status", "")),
                    started_at=started,
                    ended_at=ended,
                    duration_seconds=duration,
                    counts=getattr(row, "counts", None) or {},
                    warnings=list(getattr(row, "warnings", None) or []),
                    error=getattr(row, "error", None),
                )
            )
        return out

    @cached_property
    def tools_used(self) -> list[str]:
        try:
            from stages.registry import stages as stage_specs  # noqa: PLC0415
        except ImportError:
            return []
        specs = {spec.name: spec for spec in stage_specs()}
        names: set[str] = set()
        for stage in self.planned_stages:
            spec = specs.get(stage)
            if spec:
                names.update(spec.tools)
        return sorted(names)

    def trend(self, dimension: str, limit: int = 8) -> list[int]:
        table = _TABLE[dimension]
        rows = self.session.execute(
            select(table.scan_id, func.count(), func.max(Scan.created_at).label("at"))
            .join(Scan, Scan.id == table.scan_id)
            .where(table.target_id == self.target.id)
            .group_by(table.scan_id)
            .order_by(func.max(Scan.created_at).desc())
            .limit(limit)
        ).all()
        return [int(row[1]) for row in reversed(rows)]

    def added_and_gone(
        self, dimension: str, limit: int = 40
    ) -> tuple[list[str], list[str], int, int]:
        """What this run holds that the previous did not, and the other way round."""
        previous = self.previous_scan
        scan_id = self.scan_for(dimension)
        if previous is None or scan_id is None:
            return ([], [], 0, 0)
        table = _TABLE[dimension]
        columns = _KEY[dimension]
        label = _LABEL[dimension]
        service = dimension == _DIM.SERVICES.value

        def read(scan: UUID) -> dict[tuple, str]:
            rows = self.session.execute(
                select(*columns, label).where(table.scan_id == scan).distinct()
            )
            out: dict[tuple, str] = {}
            for row in rows:
                key = tuple(row[: len(columns)])
                out[key] = f"{row[-1]}:{key[1]}" if service else str(row[-1])
            return out

        current = read(scan_id)
        before = read(previous.id)
        added = [v for k, v in current.items() if k not in before]
        gone = [v for k, v in before.items() if k not in current]
        return (sorted(added)[:limit], sorted(gone)[:limit], len(added), len(gone))

    def excluded(self) -> dict[str, list[str]]:
        config = (self.scan.execution_config or {}) if self.scan else {}
        return {
            "hosts": list(config.get("excluded_subdomains") or []),
            "addresses": list(config.get("excluded_ips") or []),
            "paths": list(config.get("excluded_paths") or []),
        }

    def has_any(self, *dimensions: str) -> bool:
        return any(self.count_of(d) for d in dimensions)

    @cached_property
    def origin_candidates(self) -> list[tuple[str, str, str, list[str]]]:
        """Addresses answering directly that share an identity with a CDN-fronted hostname."""
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return []
        rows = self.session.execute(
            select(
                HttpAsset.host,
                HttpAsset.ip,
                HttpAsset.cdn_type,
                HttpAsset.content_hash,
                HttpAsset.tls_fingerprint,
                HttpAsset.favicon_hash,
                HttpAsset.status_code,
            ).where(
                HttpAsset.scan_id == scan_id,
                HttpAsset.status_code.is_not(None),
            )
        ).all()

        fronted: dict[tuple[str, str], set[str]] = {}
        direct: dict[tuple[str, str], set[str]] = {}
        for host, ip, cdn_type, content, tls, favicon, _status in rows:
            for kind, value in (("body", content), ("tls", tls), ("favicon", favicon)):
                if not value:
                    continue
                bucket = fronted if cdn_type in {"cdn", "waf"} else direct
                bucket.setdefault((kind, value), set()).add(
                    host if bucket is fronted else (ip or host)
                )

        out: list[tuple[str, str, str, list[str]]] = []
        seen: set[str] = set()
        for key, addresses in direct.items():
            hosts = fronted.get(key)
            if not hosts:
                continue
            for address in sorted(addresses):
                if address in seen:
                    continue
                seen.add(address)
                out.append((address, key[0], key[1][:16], sorted(hosts)[:6]))
        return out[:40]
