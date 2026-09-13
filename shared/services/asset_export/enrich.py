"""The per-chunk lookups that fill a column the row's own statement does not carry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from shared.models.port import Port
from shared.models.subdomain import Subdomain

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session

    from shared.services.asset_query import QueryScope


def ports_for(
    session: Session, scope: QueryScope, ips: Iterable[str]
) -> dict[str, list[int]]:
    """Open port numbers per address, read the way the table reads them."""
    wanted = sorted({ip for ip in ips if ip})
    if not wanted:
        return {}
    rows = session.execute(
        select(Port.ip, Port.number).where(
            scope.match(Port.scan_id), Port.ip.in_(wanted)
        )
    ).all()
    found: dict[str, set[int]] = {}
    for ip, number in rows:
        found.setdefault(ip, set()).add(number)
    return {ip: sorted(numbers) for ip, numbers in found.items()}


def hosts_for(
    session: Session, scope: QueryScope, ips: Iterable[str]
) -> dict[str, list[str]]:
    """The host names resolving to each address."""
    wanted = sorted({ip for ip in ips if ip})
    if not wanted:
        return {}
    rows = session.execute(
        select(Subdomain.name, Subdomain.resolved_ips).where(
            scope.match(Subdomain.scan_id),
            Subdomain.resolved_ips.isnot(None),
        )
    ).all()
    keep = set(wanted)
    found: dict[str, set[str]] = {}
    for name, resolved in rows:
        for ip in resolved or []:
            if ip in keep:
                found.setdefault(ip, set()).add(name)
    return {ip: sorted(names) for ip, names in found.items()}
