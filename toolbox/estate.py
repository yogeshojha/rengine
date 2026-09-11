"""What reNgine already holds about a looked-up value."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array

from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.vulnerability import Vulnerability
from shared.models.whois import WhoisRecord


@dataclass
class AddressEstate:
    rows: int = 0
    targets: int = 0
    scans: int = 0
    ports: int = 0
    last_seen: str | None = None


@dataclass
class NetworkEstate:
    hosts: int = 0
    addresses: int = 0


@dataclass
class HostEstate:
    known: set[str] = field(default_factory=set)


def _asn_hosts(project_id: uuid.UUID, asn: int):
    return (
        select(
            func.count(func.distinct(Subdomain.name)),
            func.count(func.distinct(IpAddress.ip)),
        )
        .select_from(IpAddress)
        .outerjoin(
            Subdomain,
            (Subdomain.project_id == IpAddress.project_id)
            & (Subdomain.asn == IpAddress.asn),
        )
        .where(IpAddress.project_id == project_id, IpAddress.asn == asn)
    )


def _address(project_id: uuid.UUID, ip: str):
    return select(
        func.count(IpAddress.id),
        func.count(func.distinct(IpAddress.target_id)),
        func.count(func.distinct(IpAddress.scan_id)),
        func.max(IpAddress.discovered_at),
    ).where(IpAddress.project_id == project_id, IpAddress.ip == ip)


def _ports(project_id: uuid.UUID, ip: str):
    return select(func.count(func.distinct(Port.number))).where(
        Port.project_id == project_id, Port.ip == ip
    )


def _known_hosts(project_id: uuid.UUID, names: list[str]):
    return select(func.distinct(Subdomain.name)).where(
        Subdomain.project_id == project_id, Subdomain.name.in_(names)
    )


def _cve_findings(project_id: uuid.UUID, cve: str):
    return select(func.count(Vulnerability.id)).where(
        Vulnerability.project_id == project_id,
        func.jsonb_exists_any(cast(Vulnerability.cve_ids, JSONB), pg_array([cve])),
    )


def _registrant_domains(project_id: uuid.UUID, registrant: str, exclude: str):
    return (
        select(func.count(func.distinct(WhoisRecord.query_value)))
        .join(Target, Target.target_value == WhoisRecord.query_value)
        .where(
            Target.project_id == project_id,
            WhoisRecord.registrant_name == registrant,
            WhoisRecord.query_value != exclude,
        )
    )


async def address(session, project_id: uuid.UUID | None, ip: str) -> AddressEstate:
    if project_id is None:
        return AddressEstate()
    row = (await session.execute(_address(project_id, ip))).first()
    ports = await session.scalar(_ports(project_id, ip))
    return AddressEstate(
        rows=int(row[0] or 0),
        targets=int(row[1] or 0),
        scans=int(row[2] or 0),
        ports=int(ports or 0),
        last_seen=row[3].isoformat() if row[3] else None,
    )


async def network(
    session, project_id: uuid.UUID | None, asn: int | None
) -> NetworkEstate:
    if project_id is None or asn is None:
        return NetworkEstate()
    row = (await session.execute(_asn_hosts(project_id, asn))).first()
    return NetworkEstate(hosts=int(row[0] or 0), addresses=int(row[1] or 0))


async def cve_findings(session, project_id: uuid.UUID | None, cve: str) -> int:
    if project_id is None:
        return 0
    return int(await session.scalar(_cve_findings(project_id, cve)) or 0)


async def registrant_domains(
    session, project_id: uuid.UUID | None, registrant: str, exclude: str
) -> int:
    if project_id is None or not registrant:
        return 0
    return int(
        await session.scalar(_registrant_domains(project_id, registrant, exclude)) or 0
    )


def known_hosts_sync(
    session, project_id: uuid.UUID | None, names: list[str]
) -> set[str]:
    if project_id is None or not names:
        return set()
    return set(session.execute(_known_hosts(project_id, names)).scalars().all())


def network_sync(
    session, project_id: uuid.UUID | None, asn: int | None
) -> NetworkEstate:
    if project_id is None or asn is None:
        return NetworkEstate()
    row = session.execute(_asn_hosts(project_id, asn)).first()
    return NetworkEstate(hosts=int(row[0] or 0), addresses=int(row[1] or 0))
