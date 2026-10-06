from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, cast, distinct, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import Session, aliased

from reports.data.models import (
    Address,
    Certificate,
    DimensionCoverage,
    EndpointRow,
    Facet,
    Finding,
    Host,
    HygieneCount,
    HygieneHost,
    HygieneRollup,
    PostureRollup,
    PostureZone,
    Service,
)
from shared.definitions import domain_posture as posture_defs
from shared.definitions import hygiene as hygiene_defs
from shared.definitions.correlation import MIN_BODY_BYTES
from shared.definitions.ports import SENSITIVE_PORTS, ServiceClass
from shared.definitions.reports import MAX_REPORT_ROWS, ReportScope
from shared.definitions.secrets import DETECTOR_LABELS
from shared.definitions.surface import SURFACE_ORDER, SurfaceDimension
from shared.definitions.vulnerabilities import (
    SUPPRESSED_STATES,
    Severity,
    severity_rank,
)
from shared.enums.scan import ACTIVITY_STARTED_STATUSES, ScanStatus
from shared.models.domain_posture import DomainPosture
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.secret import Secret
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.vulnerability import (
    Vulnerability,
    VulnerabilityCoverage,
    VulnerabilityTriage,
)
from shared.services.asset_query import predicates as preds
from shared.services.scan_scope import census_only, covers
from shared.services.surface_query import vulnerabilities as surface_vulns
from shared.utils.datetime import utc_now
from shared.utils.net import host_port, is_registry_routable

_DIM = SurfaceDimension
_MAX_HOSTS_PER_IP = 6
_SERVER_ERROR = 500
_TABLE = {
    _DIM.WEB_ASSETS.value: Subdomain,
    _DIM.IPS.value: IpAddress,
    _DIM.SERVICES.value: Port,
    _DIM.ENDPOINTS.value: Endpoint,
    _DIM.VULNERABILITIES.value: Vulnerability,
    _DIM.SECRETS.value: Secret,
}
_KEY = {
    _DIM.WEB_ASSETS.value: (Subdomain.name,),
    _DIM.IPS.value: (IpAddress.ip,),
    _DIM.SERVICES.value: (Port.ip, Port.number, Port.protocol),
    _DIM.ENDPOINTS.value: (Endpoint.signature,),
    _DIM.VULNERABILITIES.value: (Vulnerability.fingerprint,),
    _DIM.SECRETS.value: (Secret.fingerprint,),
}
_LABEL = {
    _DIM.WEB_ASSETS.value: (Subdomain.name,),
    _DIM.IPS.value: (IpAddress.ip,),
    _DIM.SERVICES.value: (Port.ip,),
    _DIM.ENDPOINTS.value: (func.concat(Endpoint.host, Endpoint.path),),
    _DIM.VULNERABILITIES.value: (Vulnerability.matched_at,),
    _DIM.SECRETS.value: (Secret.kind, Secret.host),
}

# the dimensions a report counts: those with a per-scan table above
REPORT_DIMENSIONS: tuple[str, ...] = tuple(d for d in SURFACE_ORDER if d in _TABLE)


def _started():
    return func.coalesce(Scan.started_at, Scan.created_at)


def _change_label(dimension: str, key: tuple, values: tuple) -> str:
    if dimension == _DIM.SERVICES.value:
        return host_port(values[0], key[1])
    if dimension == _DIM.SECRETS.value:
        kind, host = values
        label = DETECTOR_LABELS.get(kind, kind)
        return f"{label} on {host}" if host else label
    return str(values[0])


class ReportSource:
    """Reads for one scan, or per dimension for a target's latest census run."""

    def __init__(
        self,
        session: Session,
        *,
        scope: str,
        scan: Scan | None,
        target: Target,
    ) -> None:
        self.session = session
        self.scope = scope
        self.scan = scan
        self.target = target
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

    def _latest_census(self, table, dimension: str | None = None) -> UUID | None:
        ran = (
            covers(table, dimension)
            if dimension
            else select(1).where(table.scan_id == Scan.id).exists()
        )
        return self.session.execute(
            select(Scan.id)
            .where(Scan.target_id == self.target.id, census_only(), ran)
            .order_by(_started().desc())
            .limit(1)
        ).scalar()

    def scan_for(self, dimension: str) -> UUID | None:
        """The run whose rows this dimension is reported from."""
        if self.is_scan_scope:
            return self.scan.id if self.scan else None
        key = f"scan_for:{dimension}"
        if key not in self._memo:
            self._memo[key] = self._latest_census(_TABLE[dimension], dimension)
        return self._memo[key]

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
                    census_only(),
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
    def stage_results(self) -> dict[str, str]:
        """Stages the run started, in the order they ran, with their latest status."""
        if self.scan is None:
            return {}
        from stages.registry import stage_by_name  # noqa: PLC0415

        known = stage_by_name()
        rows = self.session.execute(
            select(ScanActivity.name, ScanActivity.status)
            .where(
                ScanActivity.scan_id == self.scan.id,
                ScanActivity.status.in_(ACTIVITY_STARTED_STATUSES),
            )
            .order_by(
                ScanActivity.started_at.asc().nulls_last(), ScanActivity.created_at
            )
        ).all()
        results: dict[str, str] = {}
        for name, status in rows:
            if name in known:
                results.pop(name, None)
                results[name] = status
        return results

    def _count(self, dimension: str, scan_id: UUID | None) -> int:
        if scan_id is None:
            return 0
        table = _TABLE[dimension]
        query = select(func.count()).select_from(table).where(table.scan_id == scan_id)
        if dimension == _DIM.VULNERABILITIES.value:
            query = query.where(self._not_suppressed())
        return int(self.session.execute(query).scalar() or 0)

    def _covers(self, dimension: str, scan_id: UUID | None) -> bool:
        if scan_id is None:
            return False
        return (
            self.session.execute(
                select(Scan.id).where(
                    Scan.id == scan_id, covers(_TABLE[dimension], dimension)
                )
            ).first()
            is not None
        )

    @cached_property
    def coverage(self) -> dict[str, DimensionCoverage]:
        out: dict[str, DimensionCoverage] = {}
        for dimension in REPORT_DIMENSIONS:
            scan_id = self.scan_for(dimension)
            count = self._count(dimension, scan_id)
            observed = None
            if scan_id is not None:
                run = self.session.get(Scan, scan_id)
                if run is not None:
                    observed = run.completed_at or run.started_at or run.created_at
            out[dimension] = DimensionCoverage(
                dimension=dimension,
                covered=count > 0 or self._covers(dimension, scan_id),
                count=count,
                observed_at=observed,
            )
        self._attach_previous(out)
        return out

    def _attach_previous(self, coverage: dict[str, DimensionCoverage]) -> None:
        previous = self.previous_scan
        if previous is None:
            return
        for dimension, entry in coverage.items():
            if not entry.covered or dimension not in self.previous_dimensions:
                continue
            entry.previous = self._count(dimension, previous.id)

    @cached_property
    def previous_dimensions(self) -> frozenset[str]:
        """The dimensions the previous run covered."""
        previous = self.previous_scan
        if previous is None:
            return frozenset()
        return frozenset(d for d in REPORT_DIMENSIONS if self._covers(d, previous.id))

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
    def _suppressed():
        return (
            select(VulnerabilityTriage.id)
            .where(
                VulnerabilityTriage.target_id == Vulnerability.target_id,
                VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
                VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
            )
            .exists()
        )

    @classmethod
    def _not_suppressed(cls):
        return ~cls._suppressed()

    @cached_property
    def findings(self) -> list[Finding]:
        scan_id = self.scan_for(_DIM.VULNERABILITIES.value)
        if scan_id is None:
            return []
        rows = (
            self.session.execute(
                select(Vulnerability)
                .where(Vulnerability.scan_id == scan_id, self._not_suppressed())
                .order_by(
                    surface_vulns.severity_rank(),
                    Vulnerability.is_kev.desc(),
                    Vulnerability.epss_score.desc().nulls_last(),
                    Vulnerability.id,
                )
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
            asset = assets.get(row.host or "")
            out.append(
                Finding(
                    template_id=row.template_id,
                    name=row.template_name,
                    severity=row.severity,
                    matched_at=row.matched_at,
                    host=row.host,
                    ip=row.ip,
                    description=row.description,
                    impact=row.impact,
                    remediation=row.remediation,
                    references=list(row.references or []),
                    tags=list(row.tags or []),
                    cve_ids=list(row.cve_ids or []),
                    cwe_ids=list(row.cwe_ids or []),
                    cvss_score=row.cvss_score,
                    epss_score=row.epss_score,
                    is_kev=row.is_kev,
                    is_new=known and (row.fingerprint,) not in baseline,
                    extracted=[str(v) for v in (row.extracted_results or [])],
                    request=row.request,
                    response=row.response,
                    curl=row.curl_command,
                    screenshot=asset[0] if asset else None,
                    asset_title=asset[1] if asset else None,
                    asset_status=asset[2] if asset else None,
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
            ).where(
                Subdomain.scan_id == scan_id, Subdomain.name.in_(list(hosts)[:2000])
            )
        ).all()
        return {row[0]: (row[1], row[2], row[3]) for row in rows}

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
        scan_id = self.scan_for(_DIM.VULNERABILITIES.value)
        if scan_id is None:
            return counts
        rows = self.session.execute(
            select(Vulnerability.severity, func.count())
            .where(Vulnerability.scan_id == scan_id, self._not_suppressed())
            .group_by(Vulnerability.severity)
        ).all()
        for severity, count in rows:
            counts[severity] = counts.get(severity, 0) + int(count)
        return counts

    @cached_property
    def suppressed_count(self) -> int:
        scan_id = self.scan_for(_DIM.VULNERABILITIES.value)
        if scan_id is None:
            return 0
        return int(
            self.session.execute(
                select(func.count())
                .select_from(Vulnerability)
                .where(Vulnerability.scan_id == scan_id, self._suppressed())
            ).scalar()
            or 0
        )

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
            found = by_host.get(sub.name)
            out.append(
                Host(
                    name=sub.name,
                    status=sub.http_status,
                    title=sub.page_title,
                    url=sub.http_url,
                    ips=list(sub.resolved_ips or []),
                    tech=list((asset.tech if asset else None) or sub.tech or []),
                    webserver=sub.webserver,
                    is_cdn=bool(asset.is_cdn if asset else sub.is_cdn),
                    cdn_name=(asset.cdn_name if asset else None) or sub.cdn_name,
                    waf=(asset.waf if asset else None) or sub.waf,
                    asn_org=sub.asn_org or (asset.asn_org if asset else None),
                    tls_not_after=(asset.tls_not_after if asset else None)
                    or sub.tls_not_after,
                    screenshot=sub.screenshot_path,
                    is_new=known and (sub.name,) not in baseline,
                    findings=found[0] if found else 0,
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
    def answered_hosts(self) -> list[Host]:
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
                asn=row.asn,
                asn_org=row.asn_org,
                country=row.country,
                is_cdn=row.is_cdn,
                cdn_name=row.cdn_name,
                scan_policy=row.scan_policy,
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
        rows = (
            self.session.execute(
                select(Port)
                .where(Port.scan_id == scan_id)
                .order_by(Port.ip, Port.number)
                .limit(MAX_REPORT_ROWS)
            )
            .scalars()
            .all()
        )
        hosts = self._hosts_per_ip()
        return [
            Service(
                ip=port.ip,
                port=port.number,
                service_name=port.service_name,
                service_class=port.service_class,
                product=port.product,
                version=port.version,
                banner=port.banner,
                is_http=port.is_http,
                tls=port.tls,
                sensitive=port.number in SENSITIVE_PORTS,
                hosts=hosts.get(port.ip, []),
            )
            for port in rows
        ]

    @cached_property
    def sensitive_services(self) -> list[Service]:
        return [s for s in self.service_rows if s.sensitive]

    @cached_property
    def internal_estate(self) -> bool:
        """Every address answered is private."""
        addresses = {s.ip for s in self.service_rows if s.ip}
        return bool(addresses) and not any(is_registry_routable(ip) for ip in addresses)

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
                host=row.host,
                path=row.path,
                status=row.status_code,
                endpoint_class=row.endpoint_class,
                params=list(row.params or []),
                interest=list(row.interest or []),
                is_new=known and (row.signature,) not in baseline,
            )
            for row in rows
        ]

    # ---------- hygiene ----------

    @cached_property
    def hygiene(self) -> HygieneRollup | None:
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return None
        issues = cast(Subdomain.hygiene_issues, JSONB)
        checked = cast(Subdomain.hygiene_checked, JSONB)
        warning_keys = pg_array(list(hygiene_defs.WARNING_KEYS))
        info_keys = pg_array(list(hygiene_defs.INFO_KEYS))
        columns = [
            func.count()
            .filter(Subdomain.hygiene_checked.isnot(None))
            .label("evaluated"),
            func.count()
            .filter(
                and_(
                    Subdomain.http_status.isnot(None),
                    Subdomain.hygiene_checked.is_(None),
                )
            )
            .label("pending"),
            func.count()
            .filter(
                and_(
                    func.jsonb_array_length(checked) > 0,
                    func.jsonb_array_length(issues) == 0,
                )
            )
            .label("clean"),
            func.count()
            .filter(func.jsonb_exists_any(issues, warning_keys))
            .label("warning"),
            func.count().filter(func.jsonb_exists_any(issues, info_keys)).label("info"),
        ]
        for key in hygiene_defs.CHECK_KEYS:
            columns.append(
                func.count().filter(func.jsonb_exists(issues, key)).label(f"f_{key}")
            )
            columns.append(
                func.count().filter(func.jsonb_exists(checked, key)).label(f"a_{key}")
            )
        row = (
            self.session.execute(
                select(*columns)
                .select_from(Subdomain)
                .where(Subdomain.scan_id == scan_id)
            )
            .one()
            ._mapping
        )
        host_rows = self.session.execute(
            select(Subdomain.name, Subdomain.hygiene_issues)
            .where(
                Subdomain.scan_id == scan_id,
                func.jsonb_exists_any(issues, warning_keys),
            )
            .order_by(
                preds.hygiene_length(Subdomain.hygiene_issues).desc(), Subdomain.name
            )
            .limit(MAX_REPORT_ROWS)
        ).all()
        labels = {c.key: c.label for c in hygiene_defs.CHECKS}
        order = hygiene_defs.CHECK_ORDER
        return HygieneRollup(
            evaluated=int(row["evaluated"]),
            pending=int(row["pending"]),
            clean=int(row["clean"]),
            warning=int(row["warning"]),
            info=int(row["info"]),
            checks=[
                HygieneCount(
                    key=key,
                    failing=int(row[f"f_{key}"]),
                    applicable=int(row[f"a_{key}"]),
                )
                for key in hygiene_defs.CHECK_KEYS
            ],
            hosts=[
                HygieneHost(
                    name=name,
                    checks=[
                        labels.get(k, k)
                        for k in sorted(keys or [], key=lambda k: order.get(k, 99))
                        if k in hygiene_defs.WARNING_KEYS
                    ],
                )
                for name, keys in host_rows
            ],
        )

    # ---------- domain posture ----------

    @cached_property
    def domain_posture(self) -> PostureRollup | None:
        scan_id = self.scan.id if self.is_scan_scope and self.scan else None
        if scan_id is None:
            scan_id = self._latest_census(DomainPosture)
        if scan_id is None:
            return None
        rows = (
            self.session.execute(
                select(DomainPosture)
                .where(DomainPosture.scan_id == scan_id)
                .order_by(DomainPosture.hosts.desc(), DomainPosture.zone)
            )
            .scalars()
            .all()
        )
        if not rows:
            return None
        warning_keys = set(posture_defs.WARNING_KEYS)
        spoof_keys = set(posture_defs.SPOOFABLE_KEYS)
        failing: dict[str, int] = dict.fromkeys(posture_defs.CHECK_KEYS, 0)
        applicable: dict[str, int] = dict.fromkeys(posture_defs.CHECK_KEYS, 0)
        warning = info = clean = spoofable = 0
        labels = {c.key: c.label for c in posture_defs.CHECKS}
        order = posture_defs.CHECK_ORDER
        zones: list[PostureZone] = []
        for r in rows:
            issues = set(r.posture_issues or [])
            for key in r.posture_checked or []:
                if key in applicable:
                    applicable[key] += 1
            for key in issues:
                if key in failing:
                    failing[key] += 1
            if issues & warning_keys:
                warning += 1
            elif issues:
                info += 1
            else:
                clean += 1
            if issues & spoof_keys:
                spoofable += 1
            zones.append(
                PostureZone(
                    zone=r.zone,
                    parent=r.parent,
                    hosts=r.hosts,
                    spf_all=r.spf_all,
                    dmarc_policy=r.dmarc_policy,
                    dnssec=r.dnssec,
                    checks=[
                        labels.get(k, k)
                        for k in sorted(issues, key=lambda k: order.get(k, 99))
                    ],
                )
            )
        return PostureRollup(
            evaluated=len(rows),
            zone_count=sum(1 for r in rows if r.parent is None),
            mail_hosts=sum(1 for r in rows if r.parent is not None),
            clean=clean,
            warning=warning,
            info=info,
            spoofable=spoofable,
            checks=[
                HygieneCount(key=key, failing=failing[key], applicable=applicable[key])
                for key in posture_defs.CHECK_KEYS
            ],
            zones=zones[:MAX_REPORT_ROWS],
        )

    # ---------- certificates ----------

    @cached_property
    def certificates(self) -> list[Certificate]:
        scan_id = self.scan_for(_DIM.WEB_ASSETS.value)
        if scan_id is None:
            return []
        rows = self.session.execute(
            select(
                HttpAsset.host,
                HttpAsset.tls_issuer_org,
                HttpAsset.tls_issuer_cn,
                HttpAsset.tls_not_after,
                HttpAsset.tls_expired,
                HttpAsset.tls_self_signed,
            )
            .where(HttpAsset.scan_id == scan_id, HttpAsset.tls_not_after.is_not(None))
            .distinct(HttpAsset.host)
            .order_by(HttpAsset.host, HttpAsset.id)
            .limit(MAX_REPORT_ROWS)
        ).all()
        now = self.observed_at or utc_now()
        out: list[Certificate] = []
        for host, issuer_org, issuer_cn, expires, expired, self_signed in rows:
            days = None
            if expires is not None:
                try:
                    days = (expires - now).days
                except TypeError:
                    days = None
            out.append(
                Certificate(
                    host=host,
                    issuer=issuer_org or issuer_cn,
                    not_after=expires,
                    expired=expired,
                    self_signed=self_signed,
                    days_left=days,
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
    def tools_used(self) -> list[str]:
        from stages.registry import stage_by_name  # noqa: PLC0415

        specs = stage_by_name()
        names: set[str] = set()
        for stage in self.stage_results:
            spec = specs.get(stage)
            if spec:
                names.update(spec.tools)
        return sorted(names)

    def trend(self, dimension: str, limit: int = 8) -> list[int]:
        table = _TABLE[dimension]
        runs = (
            select(Scan.id, Scan.created_at)
            .where(
                Scan.target_id == self.target.id,
                census_only(),
                covers(table, dimension),
            )
            .order_by(Scan.created_at.desc())
            .limit(limit)
            .subquery()
        )
        count = (
            select(func.count()).select_from(table).where(table.scan_id == runs.c.id)
        )
        if dimension == _DIM.VULNERABILITIES.value:
            count = count.where(self._not_suppressed())
        rows = self.session.execute(
            select(count.scalar_subquery())
            .select_from(runs)
            .order_by(runs.c.created_at)
        ).all()
        return [int(row[0] or 0) for row in rows]

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
        labels = _LABEL[dimension]

        def read(scan: UUID) -> dict[tuple, str]:
            rows = self.session.execute(
                select(*columns, *labels).where(table.scan_id == scan).distinct()
            )
            out: dict[tuple, str] = {}
            for row in rows:
                key = tuple(row[: len(columns)])
                out[key] = _change_label(dimension, key, tuple(row[len(columns) :]))
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
                HttpAsset.content_length,
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
        for host, ip, cdn_type, content, length, tls, favicon, status in rows:
            body = (
                f"{status}:{content}"
                if content and (length or 0) >= MIN_BODY_BYTES
                else None
            )
            for kind, value in (("body", body), ("tls", tls), ("favicon", favicon)):
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
