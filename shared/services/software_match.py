"""Match the software an asset reports against the NVD corpus. Nothing is sent to the asset."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.definitions.software import (
    LOW_CAVEATS,
    MAX_MATCHES_PER_SCAN,
    MEDIUM_CAVEATS,
    PRODUCTS_BY_KEY,
    Caveat,
    Confidence,
    VersionSource,
)
from shared.definitions.threat_intel import (
    SIGNALS_BY_KIND,
    ExploitSignal,
    exploit_score,
)
from shared.definitions.vulnerabilities import Severity
from shared.enums.scan import ScanScope, ScanStatus
from shared.logging import get_logger
from shared.models.software import SoftwareComponentRead, SoftwareCoverage
from shared.utils.datetime import utc_now
from shared.utils.software import (
    components_of,
    normalize_product,
    version_key,
    version_kind,
)

logger = get_logger(__name__)

LIKELY_EPSS = 0.088
_BACKFILL_CHUNK = 2000
_MAX_UNMAPPED_SHOWN = 25

_TEMP = """
CREATE TEMP TABLE software_components (
    ref uuid,
    host varchar(500),
    ip varchar(45),
    port integer,
    url varchar(2000),
    http_asset_id uuid,
    port_id uuid,
    name varchar(120),
    version varchar(64),
    version_key varchar(160),
    version_kind varchar(1),
    vendor varchar(200),
    product varchar(200),
    source varchar(16),
    distro varchar(40),
    coarse boolean
) ON COMMIT DROP
"""

_INSERT = """
INSERT INTO software_cves (
    id, scan_id, target_id, project_id, fingerprint, cve,
    name, version, vendor, product, cpe, version_source,
    severity, cvss_score, epss_score, epss_percentile,
    is_kev, kev_ransomware, kev_due_date, exploit_score, intel_kinds,
    confidence, caveats, host, ip, port, url,
    http_asset_id, port_id, discovered_at, created_at
)
SELECT DISTINCT ON (fingerprint) * FROM (
    SELECT
        gen_random_uuid() AS id,
        cast(:scan_id AS uuid) AS scan_id,
        cast(:target_id AS uuid) AS target_id,
        cast(:project_id AS uuid) AS project_id,
        md5(
            coalesce(c.host, c.ip, '') || '|' || coalesce(c.port::text, '') || '|' ||
            m.vendor || '|' || m.product || '|' || c.version || '|' || m.cve
        ) AS fingerprint,
        m.cve,
        c.name,
        c.version,
        m.vendor,
        m.product,
        'cpe:2.3:a:' || m.vendor || ':' || m.product || ':' || c.version
            || ':*:*:*:*:*:*:*' AS cpe,
        cast(c.source AS varchar) AS version_source,
        cast(coalesce(v.severity, :unknown) AS varchar) AS severity,
        v.cvss_score,
        e.score AS epss_score,
        e.percentile AS epss_percentile,
        (k.cve IS NOT NULL) AS is_kev,
        coalesce(k.known_ransomware, false) AS kev_ransomware,
        k.due_date AS kev_due_date,
        0 AS exploit_score,
        '[]'::json AS intel_kinds,
        cast(:high AS varchar) AS confidence,
        (
            SELECT coalesce(json_agg(x), '[]'::json) FROM (
                SELECT :conditional AS x WHERE m.conditional
                UNION ALL
                SELECT :backport WHERE c.distro IS NOT NULL
                UNION ALL
                SELECT :fingerprint WHERE c.source = :fingerprint_source
                UNION ALL
                SELECT :coarse WHERE c.coarse
            ) caveat
        ) AS caveats,
        c.host,
        c.ip,
        c.port,
        c.url,
        c.http_asset_id,
        c.port_id,
        cast(:now AS timestamptz) AS discovered_at,
        cast(:now AS timestamptz) AS created_at
    FROM software_components c
    JOIN nvd_cpe_matches m
      ON m.product = c.product
     AND (c.vendor IS NULL OR m.vendor = c.vendor)
     AND m.version_kind = c.version_kind
     AND (m.exact_key IS NULL OR m.exact_key = c.version_key)
     AND (m.start_key IS NULL OR c.version_key > m.start_key
          OR (m.start_incl AND c.version_key = m.start_key))
     AND (m.end_key IS NULL OR c.version_key < m.end_key
          OR (m.end_incl AND c.version_key = m.end_key))
    LEFT JOIN nvd_cves v ON v.cve = m.cve
    LEFT JOIN epss_scores e ON e.cve = m.cve
    LEFT JOIN kev_entries k ON k.cve = m.cve
) rows
ORDER BY fingerprint
LIMIT :cap
ON CONFLICT (scan_id, fingerprint) DO NOTHING
"""

_COMPONENTS = """
SELECT id, host, ip, port, url, software
  FROM http_assets
 WHERE scan_id = :scan_id
   AND json_array_length(software) > 0
"""

_PORT_COMPONENTS = """
SELECT id, ip, number, product, version
  FROM ports
 WHERE scan_id = :scan_id
   AND product IS NOT NULL
   AND version IS NOT NULL
   AND version <> ''
"""


@dataclass
class _Component:
    ref: uuid.UUID
    host: str | None
    ip: str | None
    port: int | None
    url: str | None
    http_asset_id: uuid.UUID | None
    port_id: uuid.UUID | None
    name: str
    version: str
    version_key: str
    version_kind: str
    vendor: str | None
    product: str
    source: str
    distro: str | None
    coarse: bool


_SEGMENTS_FOR_PRECISION = 2


def _is_coarse(version: str) -> bool:
    """A bare major version matches every release in its series."""
    return len([p for p in version.split(".") if p]) < _SEGMENTS_FOR_PRECISION


def _resolve(name: str, version: str) -> tuple[str | None, str] | None:
    spec = PRODUCTS_BY_KEY.get(normalize_product(name))
    if spec is None or not version:
        return None
    return spec.vendor, spec.product


def _gather(
    session: Session, scan_id: uuid.UUID
) -> tuple[list[_Component], list[tuple[str, str]]]:
    found: list[_Component] = []
    unmapped: list[tuple[str, str]] = []

    for row in session.execute(text(_COMPONENTS), {"scan_id": str(scan_id)}):
        for entry in row.software or []:
            name = (entry or {}).get("name") or ""
            version = (entry or {}).get("version") or ""
            key = version_key(version)
            if not name or not key:
                continue
            pair = _resolve(name, version)
            if pair is None:
                unmapped.append((name, entry.get("source") or ""))
                continue
            vendor, product = pair
            found.append(
                _Component(
                    ref=uuid.uuid4(),
                    host=row.host,
                    ip=row.ip,
                    port=row.port,
                    url=row.url,
                    http_asset_id=row.id,
                    port_id=None,
                    name=name,
                    version=version,
                    version_key=key,
                    version_kind=version_kind(key) or "n",
                    vendor=vendor,
                    product=product,
                    source=entry.get("source") or VersionSource.FINGERPRINT.value,
                    distro=entry.get("distro"),
                    coarse=_is_coarse(version),
                )
            )

    for row in session.execute(text(_PORT_COMPONENTS), {"scan_id": str(scan_id)}):
        key = version_key(row.version)
        if not key:
            continue
        pair = _resolve(row.product, row.version)
        if pair is None:
            unmapped.append((row.product, VersionSource.BANNER.value))
            continue
        vendor, product = pair
        found.append(
            _Component(
                ref=uuid.uuid4(),
                host=None,
                ip=row.ip,
                port=row.number,
                url=None,
                http_asset_id=None,
                port_id=row.id,
                name=row.product,
                version=row.version,
                version_key=key,
                version_kind=version_kind(key) or "n",
                vendor=vendor,
                product=product,
                source=VersionSource.BANNER.value,
                distro=None,
                coarse=_is_coarse(row.version),
            )
        )
    return found, unmapped


def _signals(
    is_kev: bool, ransomware: bool, due: date | None, epss: float | None
) -> list[str]:
    kinds: list[str] = []
    if is_kev:
        kinds.append(ExploitSignal.KEV.value)
    if ransomware:
        kinds.append(ExploitSignal.RANSOMWARE.value)
    if due is not None and due < utc_now().date():
        kinds.append(ExploitSignal.OVERDUE.value)
    if epss is not None and epss >= LIKELY_EPSS:
        kinds.append(ExploitSignal.LIKELY.value)
    return [k for k in kinds if k in SIGNALS_BY_KIND]


def _rank(session: Session, scan_id: uuid.UUID) -> None:
    """One rank per CVE, applied to every row that carries it."""
    rows = session.execute(
        text(
            "SELECT DISTINCT cve, is_kev, kev_ransomware, kev_due_date, epss_score "
            "FROM software_cves WHERE scan_id = :scan_id"
        ),
        {"scan_id": str(scan_id)},
    ).all()
    if not rows:
        return
    payload = [
        {
            "cve": row.cve,
            "score": exploit_score(
                _signals(
                    row.is_kev, row.kev_ransomware, row.kev_due_date, row.epss_score
                )
            ),
            "kinds": _signals(
                row.is_kev, row.kev_ransomware, row.kev_due_date, row.epss_score
            ),
        }
        for row in rows
    ]
    session.execute(
        text(
            "UPDATE software_cves s SET exploit_score = v.score, "
            "intel_kinds = v.kinds "
            "FROM (SELECT unnest(:cves)::varchar AS cve, unnest(:scores)::int AS score, "
            "unnest(:kinds)::json AS kinds) v "
            "WHERE s.scan_id = :scan_id AND s.cve = v.cve"
        ),
        {
            "scan_id": str(scan_id),
            "cves": [p["cve"] for p in payload],
            "scores": [p["score"] for p in payload],
            "kinds": [json.dumps(p["kinds"]) for p in payload],
        },
    )


def _confidence(session: Session, scan_id: uuid.UUID) -> None:
    for value, count in (
        (Confidence.MEDIUM.value, MEDIUM_CAVEATS),
        (Confidence.LOW.value, LOW_CAVEATS),
    ):
        session.execute(
            text(
                "UPDATE software_cves SET confidence = :value "
                "WHERE scan_id = :scan_id AND json_array_length(caveats) >= :count"
            ),
            {"value": value, "scan_id": str(scan_id), "count": count},
        )


def match_scan(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
) -> SoftwareCoverage:
    """Rebuild this scan's inferred CVEs from the software its assets reported."""
    components, unmapped = _gather(session, scan_id)
    session.execute(
        text("DELETE FROM software_cves WHERE scan_id = :scan_id"),
        {"scan_id": str(scan_id)},
    )
    coverage = SoftwareCoverage(
        components=len(components) + len(unmapped),
        mapped=len(components),
        unmapped=len(unmapped),
        unmapped_names=_unmapped_read(unmapped),
    )
    if not components:
        session.commit()
        return coverage

    session.execute(text(_TEMP))
    session.execute(
        text(
            "INSERT INTO software_components (ref, host, ip, port, url, http_asset_id, "
            "port_id, name, version, version_key, version_kind, vendor, product, source, distro, coarse) "
            "VALUES (:ref, :host, :ip, :port, :url, :http_asset_id, :port_id, :name, "
            ":version, :version_key, :version_kind, :vendor, :product, :source, :distro, :coarse)"
        ),
        [
            {
                "ref": str(c.ref),
                "host": c.host,
                "ip": c.ip,
                "port": c.port,
                "url": c.url,
                "http_asset_id": str(c.http_asset_id) if c.http_asset_id else None,
                "port_id": str(c.port_id) if c.port_id else None,
                "name": c.name,
                "version": c.version,
                "version_key": c.version_key,
                "version_kind": c.version_kind,
                "vendor": c.vendor,
                "product": c.product,
                "source": c.source,
                "distro": c.distro,
                "coarse": c.coarse,
            }
            for c in components
        ],
    )
    result = session.execute(
        text(_INSERT),
        {
            "scan_id": str(scan_id),
            "target_id": str(target_id),
            "project_id": str(project_id),
            "now": utc_now(),
            "unknown": Severity.UNKNOWN.value,
            "high": Confidence.HIGH.value,
            "conditional": Caveat.CONDITIONAL.value,
            "backport": Caveat.BACKPORT.value,
            "fingerprint": Caveat.FINGERPRINT.value,
            "fingerprint_source": VersionSource.FINGERPRINT.value,
            "coarse": Caveat.COARSE.value,
            "cap": MAX_MATCHES_PER_SCAN,
        },
    )
    coverage.findings = result.rowcount or 0
    _confidence(session, scan_id)
    _rank(session, scan_id)
    session.commit()

    coverage.matched = session.execute(
        text(
            "SELECT count(DISTINCT coalesce(http_asset_id::text, port_id::text)) "
            "FROM software_cves WHERE scan_id = :scan_id"
        ),
        {"scan_id": str(scan_id)},
    ).scalar_one()
    logger.info(
        "software matched",
        scan=str(scan_id),
        components=len(components),
        findings=coverage.findings,
    )
    return coverage


def _unmapped_read(unmapped: list[tuple[str, str]]) -> list[SoftwareComponentRead]:
    counts: dict[tuple[str, str], int] = {}
    for name, source in unmapped:
        counts[(name, source)] = counts.get((name, source), 0) + 1
    ordered = sorted(counts.items(), key=lambda item: -item[1])[:_MAX_UNMAPPED_SHOWN]
    return [
        SoftwareComponentRead(
            name=name,
            version_source=source or VersionSource.FINGERPRINT.value,
            mapped=False,
            assets=count,
        )
        for (name, source), count in ordered
    ]


_LATEST_SCANS = """
SELECT DISTINCT ON (target_id) id, target_id, project_id
  FROM scans
 WHERE status = ANY(:settled)
   AND scope <> :focused
 ORDER BY target_id, coalesce(started_at, created_at) DESC
"""


def rematch_latest(session: Session) -> dict[str, int]:
    """The corpus moves without a scan, so the covering run of every target is rebuilt."""
    rows = session.execute(
        text(_LATEST_SCANS),
        {
            "settled": [ScanStatus.COMPLETED.value, ScanStatus.CANCELLED.value],
            "focused": ScanScope.FOCUSED.value,
        },
    ).all()
    scans = 0
    findings = 0
    for row in rows:
        try:
            coverage = match_scan(
                session,
                scan_id=row.id,
                target_id=row.target_id,
                project_id=row.project_id,
            )
        except Exception:
            session.rollback()
            logger.warning("software rematch failed", scan=str(row.id), exc_info=True)
            continue
        scans += 1
        findings += coverage.findings
    return {"scans": scans, "findings": findings}


BACKFILL_SCANS_PER_TICK = 5

_PENDING_SCANS = """
SELECT DISTINCT scan_id
  FROM http_assets
 WHERE json_array_length(software) = 0
   AND (json_array_length(tech) > 0 OR webserver IS NOT NULL)
 LIMIT :limit
"""

_ASSETS_TO_FILL = """
SELECT id, tech, webserver
  FROM http_assets
 WHERE scan_id = :scan_id
   AND json_array_length(software) = 0
   AND (json_array_length(tech) > 0 OR webserver IS NOT NULL)
"""


def pending_scans(
    session: Session, *, limit: int = BACKFILL_SCANS_PER_TICK
) -> list[uuid.UUID]:
    rows = session.execute(text(_PENDING_SCANS), {"limit": limit}).all()
    return [row[0] for row in rows]


def backfill_scan(session: Session, scan_id: uuid.UUID) -> int:
    """Fill software for rows httpx wrote before the column existed."""
    rows = session.execute(text(_ASSETS_TO_FILL), {"scan_id": str(scan_id)}).all()
    filled = 0
    payload = []
    for row in rows:
        entries = components_of(list(row.tech or []), row.webserver)
        payload.append({"id": str(row.id), "software": json.dumps(entries)})
        filled += 1
    for start in range(0, len(payload), _BACKFILL_CHUNK):
        session.execute(
            text(
                "UPDATE http_assets SET software = v.software::json "
                "FROM (SELECT unnest(:ids)::uuid AS id, unnest(:software)::text AS software) v "
                "WHERE http_assets.id = v.id"
            ),
            {
                "ids": [
                    item["id"] for item in payload[start : start + _BACKFILL_CHUNK]
                ],
                "software": [
                    item["software"]
                    for item in payload[start : start + _BACKFILL_CHUNK]
                ],
            },
        )
    session.commit()
    return filled
