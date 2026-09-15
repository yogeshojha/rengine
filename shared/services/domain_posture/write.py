"""Rows per zone and the fold onto the zone's hosts."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from shared.definitions.domain_posture import MAX_ZONE_LENGTH
from shared.models.domain_posture import DomainPosture
from shared.models.subdomain import Subdomain
from shared.services.domain_posture.evaluate import Posture
from shared.services.domain_posture.records import ZoneRecords
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control


def _short(value: str | None, cap: int) -> str | None:
    if value is None:
        return None
    cleaned = strip_control(value)
    return cleaned[:cap] if len(cleaned) > cap else cleaned


def row_for(
    *,
    scan_id: UUID,
    target_id: UUID,
    project_id: UUID,
    rec: ZoneRecords,
    posture: Posture,
    hosts: int,
) -> DomainPosture:
    now = utc_now()
    return DomainPosture(
        scan_id=scan_id,
        target_id=target_id,
        project_id=project_id,
        zone=rec.zone[:MAX_ZONE_LENGTH],
        parent=rec.parent[:MAX_ZONE_LENGTH] if rec.parent else None,
        hosts=hosts,
        spf=_short(posture.spf, 4000),
        spf_all=posture.spf_all,
        spf_lookups=posture.spf_lookups,
        dmarc=_short(posture.dmarc, 4000),
        dmarc_policy=_short(posture.dmarc_policy, 16),
        dmarc_subdomain_policy=_short(posture.dmarc_subdomain_policy, 16),
        dmarc_pct=posture.dmarc_pct,
        dmarc_rua=posture.dmarc_rua,
        dmarc_inherited=rec.dmarc_inherited,
        dkim_selectors=list(posture.dkim_selectors),
        dkim_key_bits=posture.dkim_key_bits,
        mx=[strip_control(v)[:253] for v in rec.mx],
        null_mx=rec.null_mx,
        mta_sts=_short(rec.mta_sts[0], 500) if rec.mta_sts else None,
        mta_sts_mode=posture.mta_sts_mode,
        tls_rpt=_short(rec.tls_rpt[0], 500) if rec.tls_rpt else None,
        dnssec=rec.dnssec,
        caa=[strip_control(v)[:500] for v in rec.caa],
        posture_issues=posture.issues,
        posture_checked=posture.checked,
        evidence={k: strip_control(v) for k, v in posture.evidence.items()},
        discovered_at=now,
        created_at=now,
    )


def replace_rows(session: Session, scan_id: UUID, rows: Iterable[DomainPosture]) -> int:
    session.execute(delete(DomainPosture).where(DomainPosture.scan_id == scan_id))
    rows = list(rows)
    session.add_all(rows)
    session.flush()
    return len(rows)


def zone_of(name: str, zones: Iterable[str]) -> str | None:
    """The longest zone the name sits under."""
    host = name.strip().lower().rstrip(".")
    best: str | None = None
    for zone in zones:
        under = host == zone or host.endswith("." + zone)
        if under and (best is None or len(zone) > len(best)):
            best = zone
    return best


_CLEAR_SQL = text(
    """
    UPDATE subdomains SET posture_issues = NULL, posture_checked = NULL
     WHERE scan_id = :scan_id
    """
)

_FOLD_SQL = text(
    """
    UPDATE subdomains
       SET posture_issues = CAST(:issues AS json),
           posture_checked = CAST(:checked AS json)
     WHERE scan_id = :scan_id AND name = ANY(:names)
    """
)


def fold_onto_hosts(session: Session, scan_id: UUID) -> int:
    """Every host carries the checks of the longest zone it sits under."""
    session.execute(_CLEAR_SQL, {"scan_id": scan_id})
    zones = session.execute(
        select(
            DomainPosture.zone,
            DomainPosture.posture_issues,
            DomainPosture.posture_checked,
        ).where(DomainPosture.scan_id == scan_id)
    ).all()
    if not zones:
        return 0
    by_zone = {z.zone: (z.posture_issues, z.posture_checked) for z in zones}
    names = session.scalars(
        select(Subdomain.name).where(Subdomain.scan_id == scan_id)
    ).all()
    grouped: dict[str, list[str]] = defaultdict(list)
    for name in names:
        zone = zone_of(name, by_zone)
        if zone is not None:
            grouped[zone].append(name)
    folded = 0
    for zone, members in grouped.items():
        issues, checked = by_zone[zone]
        folded += session.execute(
            _FOLD_SQL,
            {
                "scan_id": scan_id,
                "names": members,
                "issues": json.dumps(list(issues or [])),
                "checked": json.dumps(list(checked or [])),
            },
        ).rowcount
    return folded
