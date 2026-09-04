"""The only writer of `vulnerabilities` rows: dedupes by fingerprint and binds each finding to its asset."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from shared.definitions.vulnerabilities import SUPPRESSED_STATES
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage
from shared.utils.datetime import utc_now
from tools.nuclei.parser import Finding

logger = get_logger(__name__)

_BATCH = 500


@dataclass
class AssetIndex:
    """Every place this scan already recorded an asset, keyed the way a finding names it."""

    subdomains: dict[str, uuid.UUID]
    assets_by_url: dict[str, uuid.UUID]
    assets_by_host_port: dict[tuple[str, int], uuid.UUID]
    ports: dict[tuple[str, int], uuid.UUID]
    ip_by_host: dict[str, str]


def build_index(session: Session, scan_id: uuid.UUID) -> AssetIndex:
    subdomains: dict[str, uuid.UUID] = {}
    ip_by_host: dict[str, str] = {}
    for row in session.execute(
        select(Subdomain.id, Subdomain.name, Subdomain.resolved_ips).where(
            Subdomain.scan_id == scan_id
        )
    ):
        subdomains[row.name.lower()] = row.id
        ips = row.resolved_ips or []
        if ips:
            ip_by_host[row.name.lower()] = str(ips[0])

    assets_by_url: dict[str, uuid.UUID] = {}
    assets_by_host_port: dict[tuple[str, int], uuid.UUID] = {}
    for row in session.execute(
        select(HttpAsset.id, HttpAsset.url, HttpAsset.host, HttpAsset.port).where(
            HttpAsset.scan_id == scan_id
        )
    ):
        assets_by_url.setdefault(_normalize_url(row.url), row.id)
        assets_by_host_port.setdefault((row.host.lower(), int(row.port or 0)), row.id)

    ports: dict[tuple[str, int], uuid.UUID] = {}
    for row in session.execute(
        select(Port.id, Port.ip, Port.number).where(Port.scan_id == scan_id)
    ):
        ports.setdefault((row.ip, int(row.number)), row.id)

    return AssetIndex(
        subdomains=subdomains,
        assets_by_url=assets_by_url,
        assets_by_host_port=assets_by_host_port,
        ports=ports,
        ip_by_host=ip_by_host,
    )


def _normalize_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlsplit(value.strip())
    if not parsed.scheme:
        return value.strip().rstrip("/").lower()
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}".lower()


def _bind(finding: Finding, index: AssetIndex) -> dict:
    host = (finding.host or "").lower()
    ip = finding.ip or index.ip_by_host.get(host)
    asset_id = index.assets_by_url.get(
        _normalize_url(finding.url or finding.matched_at)
    )
    if asset_id is None and host and finding.port:
        asset_id = index.assets_by_host_port.get((host, int(finding.port)))
    port_id = None
    if ip and finding.port:
        port_id = index.ports.get((ip, int(finding.port)))
    return {
        "subdomain_id": index.subdomains.get(host),
        "http_asset_id": asset_id,
        "port_id": port_id,
        "ip": ip,
    }


def to_row(
    finding: Finding,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    index: AssetIndex,
    now,
) -> dict:
    bound = _bind(finding, index)
    return {
        "id": uuid.uuid4(),
        "scan_id": scan_id,
        "target_id": target_id,
        "project_id": project_id,
        "fingerprint": finding.fingerprint,
        "scanner": finding.scanner,
        "template_id": finding.template_id,
        "template_name": finding.template_name,
        "template_path": finding.template_path,
        "template_url": finding.template_url,
        "severity": finding.severity,
        "protocol": finding.protocol,
        "matcher_name": finding.matcher_name,
        "extractor_name": finding.extractor_name,
        "extracted_results": finding.extracted_results,
        "description": finding.description,
        "impact": finding.impact,
        "remediation": finding.remediation,
        "references": finding.references,
        "tags": finding.tags,
        "authors": finding.authors,
        "cve_ids": finding.cve_ids,
        "cwe_ids": finding.cwe_ids,
        "cvss_metrics": finding.cvss_metrics,
        "cvss_score": finding.cvss_score,
        "epss_score": finding.epss_score,
        "epss_percentile": finding.epss_percentile,
        "cpe": finding.cpe,
        "is_kev": finding.is_kev,
        "extra": finding.extra,
        "matched_at": finding.matched_at,
        "host": finding.host,
        "port": finding.port,
        "scheme": finding.scheme,
        "url": finding.url,
        "path": finding.path,
        "request": finding.request,
        "response": finding.response,
        "curl_command": finding.curl_command,
        "interaction": finding.interaction,
        "observed_at": finding.observed_at,
        "discovered_at": now,
        "created_at": now,
        **bound,
    }


def upsert(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    findings: list[Finding],
    index: AssetIndex | None = None,
) -> int:
    """Store findings for this scan. The same fingerprint twice in one scan is one row."""
    if not findings:
        return 0
    resolved = index if index is not None else build_index(session, scan_id)
    now = utc_now()
    seen: set[str] = set()
    rows: list[dict] = []
    for finding in findings:
        if finding.fingerprint in seen:
            continue
        seen.add(finding.fingerprint)
        rows.append(
            to_row(
                finding,
                scan_id=scan_id,
                target_id=target_id,
                project_id=project_id,
                index=resolved,
                now=now,
            )
        )
    rows.sort(key=lambda row: row["fingerprint"])

    written = 0
    for start in range(0, len(rows), _BATCH):
        chunk = rows[start : start + _BATCH]
        statement = (
            insert(Vulnerability)
            .values(chunk)
            .on_conflict_do_nothing(constraint="uq_vuln_scan_fingerprint")
            .returning(Vulnerability.id)
        )
        written += len(session.execute(statement).scalars().all())
    session.commit()
    return written


def suppressed(session: Session, target_id: uuid.UUID) -> set[str]:
    """Fingerprints a reviewer has already rejected or accepted for this target."""
    return set(
        session.execute(
            select(VulnerabilityTriage.fingerprint).where(
                VulnerabilityTriage.target_id == target_id,
                VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
            )
        )
        .scalars()
        .all()
    )


def known_fingerprints(
    session: Session, target_id: uuid.UUID, scan_id: uuid.UUID
) -> set[str]:
    """Fingerprints an earlier scan of this target already reported."""
    return set(
        session.execute(
            select(Vulnerability.fingerprint)
            .where(
                Vulnerability.target_id == target_id,
                Vulnerability.scan_id != scan_id,
            )
            .distinct()
        )
        .scalars()
        .all()
    )
