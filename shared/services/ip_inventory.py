"""Every IP a scan knows about, materialised once into ip_addresses and shared by stages."""

from __future__ import annotations

import ipaddress
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from shared.enums.ip import IpSource
from shared.models.ip_address import IpAddress
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

MAX_IPS = 100_000

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
    """Insert missing ip_addresses rows. Safe to call from parallel stages."""
    if not ips:
        return 0
    now = utc_now()
    # cdn_check and passive_ports insert the same rows at the same level; a UNION has no
    # guaranteed order, and two overlapping inserts taking locks in different orders deadlock
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
    return int(result.rowcount or 0)


def ensure(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[str]:
    """Collect every known IP and guarantee a row for each. Returns the address list."""
    ips = collect_ips(session, scan_id)
    materialize(
        session,
        scan_id=scan_id,
        target_id=target_id,
        project_id=project_id,
        ips=ips,
    )
    return ips
