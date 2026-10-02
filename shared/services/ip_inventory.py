"""Every IP a scan knows about, materialised into ip_addresses and enriched in the same write."""

from __future__ import annotations

import ipaddress
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert

from shared.enums.ip import IpSource
from shared.models.ip_address import IpAddress
from shared.services.ip_asn import enrich_addresses
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

MAX_IPS = 100_000
_UPSERT_BATCH = 5_000

# every table a scan can park an IP in
_COLLECT_SQL = """
SELECT ip FROM subdomains s,
       LATERAL jsonb_array_elements_text(cast(s.resolved_ips AS jsonb)) ip
WHERE s.scan_id = :sid
UNION
SELECT ip FROM http_assets WHERE scan_id = :sid AND ip IS NOT NULL
UNION
SELECT ip FROM ports WHERE scan_id = :sid
UNION
SELECT ip FROM ip_addresses WHERE scan_id = :sid
"""


def collect_ips(session: Session, scan_id: uuid.UUID) -> list[str]:
    rows = session.execute(text(_COLLECT_SQL).bindparams(sid=scan_id)).scalars()
    seen: dict[str, None] = {}
    for raw in rows:
        value = (raw or "").strip()
        if not value or value in seen:
            continue
        try:
            ipaddress.ip_address(value)
        except ValueError:
            continue
        seen[value] = None
        if len(seen) >= MAX_IPS:
            break
    return list(seen)


def materialize(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    ips: list[str],
    source: str = IpSource.DNS_RESOLUTION.value,
) -> int:
    """Insert missing ip_addresses rows."""
    if not ips:
        return 0
    now = utc_now()
    ips = sorted(set(ips))
    rows = [
        {
            "id": uuid.uuid4(),
            "scan_id": scan_id,
            "target_id": target_id,
            "project_id": project_id,
            "ip": ip,
            "version": ipaddress.ip_address(ip).version,
            "source": source,
            "ptr_hostnames": [],
            "is_cdn": False,
            "discovered_at": now,
            "created_at": now,
        }
        for ip in ips
    ]
    statement = (
        insert(IpAddress)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_ipaddress_scan_ip")
    )
    result = session.execute(statement)
    session.commit()
    enrich_addresses(session, scan_id=scan_id, ips=ips)
    session.commit()
    return int(result.rowcount or 0)


def materialize_rows(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    rows: list[dict],
) -> int:
    """Upsert addresses that carry their own source, prefix and ASN."""
    by_ip: dict[str, dict] = {}
    for row in rows:
        by_ip.setdefault(row["ip"], row)
    if not by_ip:
        return 0
    now = utc_now()
    ips = sorted(by_ip)
    values = [
        {
            "id": uuid.uuid4(),
            "scan_id": scan_id,
            "target_id": target_id,
            "project_id": project_id,
            "ip": ip,
            "version": by_ip[ip]["version"],
            "source": by_ip[ip]["source"],
            "prefix": by_ip[ip].get("prefix"),
            "asn": by_ip[ip].get("asn"),
            "ptr_hostnames": [],
            "is_cdn": False,
            "discovered_at": now,
            "created_at": now,
        }
        for ip in ips
    ]
    written = 0
    for start in range(0, len(values), _UPSERT_BATCH):
        statement = insert(IpAddress).values(values[start : start + _UPSERT_BATCH])
        statement = statement.on_conflict_do_update(
            constraint="uq_ipaddress_scan_ip",
            set_={
                "prefix": func.coalesce(IpAddress.prefix, statement.excluded.prefix),
                "asn": func.coalesce(IpAddress.asn, statement.excluded.asn),
            },
        )
        written += int(session.execute(statement).rowcount or 0)
    session.commit()
    enrich_addresses(session, scan_id=scan_id, ips=ips)
    session.commit()
    return written


def ensure(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[str]:
    """Collect every known IP and guarantee a row for each."""
    ips = collect_ips(session, scan_id)
    materialize(
        session,
        scan_id=scan_id,
        target_id=target_id,
        project_id=project_id,
        ips=ips,
    )
    return ips
