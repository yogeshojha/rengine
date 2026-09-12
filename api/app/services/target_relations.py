"""What shows that two targets in one project are the same estate."""

from __future__ import annotations

import re
from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.surface_scope import SurfaceScopeService
from shared.definitions.domains import registrable_domain
from shared.definitions.relations import (
    FAVICON_MAX_TARGETS,
    MAX_RELATED_TARGETS,
    MAX_RELATION_EVIDENCE,
    MAX_SAN_ROWS,
    RELATION_LABELS,
    RELATION_ORDER,
    TargetRelation,
)
from shared.definitions.surface import SurfaceDimension
from shared.models.dns import DnsRecord
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.relations import RelatedTarget, RelationEvidence, TargetRelations
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.whois import WhoisNameserver, WhoisRecord
from shared.services.asset_query.scope import QueryScope
from shared.utils.infra import is_shared_host, is_shared_nameserver, owns_network
from shared.utils.privacy import registrant_key

# kind -> value -> targets carrying it, with what to show for each
_Facts = dict[str, dict[str, dict[UUID, str]]]


_SPF_INCLUDE = re.compile(r"include:([^\s]+)")
_ADDRESS_RECORDS = ("A", "AAAA")


def _ours(host: str, owned: set[str]) -> bool:
    """A mail host or a zone contact identifies an estate only when the estate owns it."""
    return bool(host) and not is_shared_host(host) and registrable_domain(host) in owned


def _dns_keys(
    record_type: str, value: str, soa_email: str, cdn: set[str], owned: set[str]
) -> list[tuple[str, str]]:
    """What a record says about ownership, as (shown, key) pairs. NS is the WHOIS relation's."""
    kind = record_type.upper().removeprefix("DNSRECORDTYPE.")
    host = value.strip().lower().rstrip(".")
    if kind == "MX" and _ours(host, owned):
        return [(f"MX {host}", f"mx:{host}")]
    if kind == "SOA":
        contact = soa_email.strip().lower().rstrip(".")
        if _ours(contact, owned):
            return [(f"SOA {contact}", f"soa:{contact}")]
        return []
    if kind in _ADDRESS_RECORDS and host and host not in cdn:
        return [(f"{kind} {host}", f"address:{host}")]
    if kind == "TXT" and host.startswith("v=spf1"):
        return [
            (f"SPF include:{domain}", f"spf:{domain}")
            for domain in {
                m.group(1).lower().rstrip(".") for m in _SPF_INCLUDE.finditer(host)
            }
            if _ours(domain, owned)
        ]
    return []


def _identity(target_value: str, registrant: str) -> set[str]:
    """The names a network holder would carry if this target ran it."""
    apex = registrable_domain(target_value) or target_value
    label = apex.split(".")[0] if apex else ""
    return {key for key in (registrant_key(registrant), label.lower()) if key}


class TargetRelationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_target(self, project_id: UUID, target_id: UUID) -> TargetRelations:
        targets = await self._targets(project_id)
        if target_id not in targets or len(targets) < 2:  # noqa: PLR2004
            return TargetRelations(considered=len(targets))

        facts = await self._facts(project_id, targets)
        reasons: dict[UUID, list[RelationEvidence]] = defaultdict(list)
        for kind in RELATION_ORDER:
            for value, carriers in facts.get(kind, {}).items():
                if target_id not in carriers:
                    continue
                for other, detail in carriers.items():
                    if other == target_id or other not in targets:
                        continue
                    reasons[other].append(
                        RelationEvidence(
                            kind=kind,
                            label=RELATION_LABELS[kind],
                            value=value,
                            detail=detail,
                        )
                    )

        items = [
            RelatedTarget(
                target_id=other,
                target_value=targets[other].target_value,
                reasons=evidence[:MAX_RELATION_EVIDENCE],
            )
            for other, evidence in reasons.items()
        ]
        items.sort(
            key=lambda item: (
                RELATION_ORDER.index(item.reasons[0].kind),
                -len(item.reasons),
                item.target_value,
            )
        )
        return TargetRelations(
            items=items[:MAX_RELATED_TARGETS],
            total=len(items),
            considered=len(targets),
        )

    async def _targets(self, project_id: UUID) -> dict[UUID, Target]:
        rows = await self.session.execute(
            select(Target).where(Target.project_id == project_id)
        )
        return {row.id: row for row in rows.scalars().all()}

    async def _facts(self, project_id: UUID, targets: dict[UUID, Target]) -> _Facts:
        """Each dimension is read from the scans that covered it."""
        scopes = SurfaceScopeService(self.session)
        assets = await scopes.scope(project_id, SurfaceDimension.WEB_ASSETS.value)
        addresses = await scopes.scope(project_id, SurfaceDimension.IPS.value)
        facts: _Facts = defaultdict(lambda: defaultdict(dict))
        await self._registration(targets, facts)
        await self._dns(targets, facts)
        if assets:
            await self._certificates(assets, targets, facts)
            await self._favicons(assets, facts)
        if addresses:
            await self._networks(addresses, targets, facts)
        return facts

    async def _registration(self, targets: dict[UUID, Target], facts: _Facts) -> None:
        ids = [t.whois_record_id for t in targets.values() if t.whois_record_id]
        if not ids:
            return
        by_record = {t.whois_record_id: t.id for t in targets.values()}
        rows = await self.session.execute(
            select(WhoisRecord.id, WhoisRecord.registrant_name).where(
                WhoisRecord.id.in_(ids)
            )
        )
        for record_id, registrant in rows.all():
            key = registrant_key(registrant)
            if key:
                facts[TargetRelation.REGISTRANT.value][key][by_record[record_id]] = (
                    registrant
                )

        names = await self.session.execute(
            select(WhoisNameserver.whois_record_id, WhoisNameserver.nameserver).where(
                WhoisNameserver.whois_record_id.in_(ids)
            )
        )
        for record_id, nameserver in names.all():
            if is_shared_nameserver(nameserver):
                continue
            facts[TargetRelation.NAMESERVER.value][nameserver][by_record[record_id]] = (
                nameserver
            )

    async def _dns(self, targets: dict[UUID, Target], facts: _Facts) -> None:
        """A mail host, a zone contact or an address that is not a provider's."""
        rows = await self.session.execute(
            select(
                DnsRecord.target_id,
                DnsRecord.record_type,
                DnsRecord.value,
                DnsRecord.soa_email,
            ).where(DnsRecord.target_id.in_(list(targets)))
        )
        cdn = await self._cdn_addresses()
        owned = {
            registrable_domain(t.target_value)
            for t in targets.values()
            if registrable_domain(t.target_value)
        }
        for target_id, kind, value, soa_email in rows.all():
            for shown, key in _dns_keys(
                str(kind), value or "", soa_email or "", cdn, owned
            ):
                facts[TargetRelation.DNS_RECORD.value][key][target_id] = shown

    async def _cdn_addresses(self) -> set[str]:
        rows = await self.session.execute(
            select(IpAddress.ip).where(IpAddress.is_cdn.is_(True)).distinct()
        )
        return set(rows.scalars().all())

    async def _certificates(
        self, scope: QueryScope, targets: dict[UUID, Target], facts: _Facts
    ) -> None:
        rows = await self.session.execute(
            select(
                HttpAsset.target_id,
                HttpAsset.tls_fingerprint,
                func.min(HttpAsset.tls_subject_cn),
            )
            .where(
                scope.match(HttpAsset.scan_id), HttpAsset.tls_fingerprint.isnot(None)
            )
            .group_by(HttpAsset.target_id, HttpAsset.tls_fingerprint)
        )
        for target_id, fingerprint, subject in rows.all():
            facts[TargetRelation.CERTIFICATE.value][fingerprint][target_id] = (
                subject or ""
            )

        apexes = {
            registrable_domain(t.target_value): t.id
            for t in targets.values()
            if registrable_domain(t.target_value)
        }
        sans = await self.session.execute(
            select(HttpAsset.target_id, HttpAsset.tls_sans, HttpAsset.host)
            .where(
                scope.match(HttpAsset.scan_id), HttpAsset.tls_fingerprint.isnot(None)
            )
            .limit(MAX_SAN_ROWS)
        )
        for target_id, names, host in sans.all():
            for raw in names or []:
                apex = registrable_domain(str(raw))
                owner = apexes.get(apex)
                if owner is None or owner == target_id:
                    continue
                facts[TargetRelation.CERTIFICATE.value][f"san:{apex}"][target_id] = host
                facts[TargetRelation.CERTIFICATE.value][f"san:{apex}"][owner] = apex

    async def _favicons(self, scope: QueryScope, facts: _Facts) -> None:
        rows = await self.session.execute(
            select(Subdomain.favicon_hash, Subdomain.target_id, func.count())
            .where(
                scope.match(Subdomain.scan_id),
                Subdomain.favicon_hash.isnot(None),
                Subdomain.favicon_hash != "",
            )
            .group_by(Subdomain.favicon_hash, Subdomain.target_id)
        )
        carried: dict[str, dict[UUID, str]] = defaultdict(dict)
        for value, target_id, count in rows.all():
            carried[value][target_id] = f"{count} web assets"
        for value, owners in carried.items():
            if len(owners) <= FAVICON_MAX_TARGETS:
                facts[TargetRelation.FAVICON.value][value] = owners

    async def _networks(
        self, scope: QueryScope, targets: dict[UUID, Target], facts: _Facts
    ) -> None:
        rows = await self.session.execute(
            select(
                IpAddress.asn,
                func.min(IpAddress.asn_org),
                IpAddress.target_id,
                func.count(),
            )
            .where(scope.match(IpAddress.scan_id), IpAddress.asn.isnot(None))
            .group_by(IpAddress.asn, IpAddress.target_id)
        )
        holders: dict[int, str] = {}
        carried: dict[int, dict[UUID, str]] = defaultdict(dict)
        for asn, org, target_id, count in rows.all():
            holders[asn] = org or ""
            carried[asn][target_id] = f"{count} addresses"

        registrants = await self._registrants(targets)
        for asn, owners in carried.items():
            identities: set[str] = set()
            for target_id in owners:
                target = targets.get(target_id)
                if target is not None:
                    identities |= _identity(
                        target.target_value, registrants.get(target_id, "")
                    )
            if not owns_network(holders[asn], identities):
                continue
            value = f"AS{asn}"
            for target_id, detail in owners.items():
                facts[TargetRelation.NETWORK.value][value][target_id] = (
                    f"{holders[asn]} · {detail}" if holders[asn] else detail
                )

    async def _registrants(self, targets: dict[UUID, Target]) -> dict[UUID, str]:
        ids = [t.whois_record_id for t in targets.values() if t.whois_record_id]
        if not ids:
            return {}
        by_record = {t.whois_record_id: t.id for t in targets.values()}
        rows = await self.session.execute(
            select(WhoisRecord.id, WhoisRecord.registrant_name).where(
                WhoisRecord.id.in_(ids)
            )
        )
        return {by_record[rid]: name for rid, name in rows.all()}
