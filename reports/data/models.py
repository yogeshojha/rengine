"""Plain rows the sections render. Nothing here knows about SQL or HTML."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DimensionCoverage:
    dimension: str
    covered: bool = False
    count: int = 0
    previous: int | None = None
    added: int | None = None
    gone: int | None = None
    observed_at: datetime | None = None
    scan_id: str = ""
    note: str = ""

    @property
    def delta(self) -> int | None:
        if self.previous is None:
            return None
        return self.count - self.previous


@dataclass
class Finding:
    id: str
    fingerprint: str
    template_id: str
    name: str
    severity: str
    scanner: str
    protocol: str
    matched_at: str
    host: str | None = None
    ip: str | None = None
    port: int | None = None
    url: str | None = None
    description: str | None = None
    impact: str | None = None
    remediation: str | None = None
    references: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    cvss_score: float | None = None
    cvss_metrics: str | None = None
    epss_score: float | None = None
    is_kev: bool = False
    state: str = "open"
    note: str | None = None
    is_new: bool = False
    extracted: list[str] = field(default_factory=list)
    request: str | None = None
    response: str | None = None
    curl: str | None = None
    matcher: str | None = None
    discovered_at: datetime | None = None
    screenshot: str | None = None
    asset_title: str | None = None
    asset_status: int | None = None
    asset_tech: list[str] = field(default_factory=list)


@dataclass
class Issue:
    """One weakness, with every place it was observed."""

    template_id: str
    name: str
    severity: str
    scanner: str
    protocol: str
    description: str | None = None
    impact: str | None = None
    remediation: str | None = None
    references: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    cvss_score: float | None = None
    epss_score: float | None = None
    is_kev: bool = False
    findings: list[Finding] = field(default_factory=list)
    controls: dict[str, list[str]] = field(default_factory=dict)
    cwe_rank: int | None = None
    risk: float = 0.0
    explainer: str | None = None

    @property
    def count(self) -> int:
        return len(self.findings)

    @property
    def hosts(self) -> list[str]:
        seen: dict[str, None] = {}
        for finding in self.findings:
            key = finding.host or finding.ip or ""
            if key:
                seen.setdefault(key, None)
        return list(seen)

    @property
    def new_count(self) -> int:
        return sum(1 for f in self.findings if f.is_new)


@dataclass
class Host:
    name: str
    status: int | None = None
    title: str | None = None
    url: str | None = None
    ips: list[str] = field(default_factory=list)
    cname: str | None = None
    tech: list[str] = field(default_factory=list)
    webserver: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    cdn_type: str | None = None
    waf: str | None = None
    asn: int | None = None
    asn_org: str | None = None
    country: str | None = None
    tls_issuer: str | None = None
    tls_not_after: datetime | None = None
    tls_expired: bool | None = None
    tls_self_signed: bool | None = None
    screenshot: str | None = None
    sources: list[str] = field(default_factory=list)
    is_new: bool = False
    findings: int = 0
    worst: str | None = None
    endpoints: int = 0


@dataclass
class Address:
    ip: str
    version: int = 4
    asn: int | None = None
    asn_org: str | None = None
    country: str | None = None
    prefix: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    cdn_type: str | None = None
    scan_policy: str | None = None
    scan_policy_reason: str | None = None
    ptr: list[str] = field(default_factory=list)
    open_ports: int = 0
    hosts: list[str] = field(default_factory=list)
    is_new: bool = False


@dataclass
class Service:
    ip: str
    port: int
    protocol: str = "tcp"
    service_name: str | None = None
    service_class: str = "other"
    product: str | None = None
    version: str | None = None
    banner: str | None = None
    is_http: bool = False
    tls: bool = False
    source: str = ""
    sensitive: bool = False
    hosts: list[str] = field(default_factory=list)
    status: int | None = None
    title: str | None = None
    asn_org: str | None = None
    country: str | None = None
    is_new: bool = False


@dataclass
class EndpointRow:
    url: str
    host: str
    path: str
    status: int | None = None
    endpoint_class: str = "other"
    content_type: str | None = None
    length: int | None = None
    title: str | None = None
    params: list[str] = field(default_factory=list)
    interest: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    is_probed: bool = False
    is_new: bool = False


@dataclass
class Certificate:
    host: str
    subject: str | None = None
    issuer: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    expired: bool | None = None
    self_signed: bool | None = None
    days_left: int | None = None
    sans: int = 0
    version: str | None = None


@dataclass
class StageRun:
    name: str
    title: str
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    counts: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class Facet:
    name: str
    count: int
    label: str = ""
    extra: str = ""


@dataclass
class Delta:
    dimension: str
    added: list[str] = field(default_factory=list)
    gone: list[str] = field(default_factory=list)
    added_total: int = 0
    gone_total: int = 0
