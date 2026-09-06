from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from shared.definitions.domains import (
    MAX_RELATED_DOMAINS,
    MAX_RELATED_HOSTNAMES,
    PRIVATE_TLDS,
    RELATED_REASON_DETAIL,
    RELATED_REASON_LABELS,
    VENDOR_DOMAINS,
    RelatedReason,
    registrable_domain,
)
from shared.models.http_asset import HttpAsset
from shared.models.related import RelatedDomain, RelatedDomains, RelatedEvidence
from shared.models.subdomain import Subdomain
from shared.models.target import Target

_MAX_TRUST_PASSES = 3


@dataclass(frozen=True)
class Cert:
    """One certificate a scan saw, and whether it is ours to read names from."""

    host_root: str
    cn_root: str
    names: set[str]
    host: str
    fronted: bool

    def ours(self, trusted: set[str]) -> bool:
        # the subject is often a sibling brand rather than the host, so a certificate
        # a host of ours served counts too — unless a CDN served it, where it is theirs
        if self.cn_root and self.cn_root in trusted:
            return True
        return not self.fronted and bool(self.host_root) and self.host_root in trusted


def _clean(value: str | None) -> str:
    if not value:
        return ""
    host = value.strip().lower().rstrip(".").removeprefix("*.")
    return host if "." in host and " " not in host else ""


class RelatedDomainService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_scan(self, project_id: UUID, scan_id: UUID) -> RelatedDomains:
        target_value = await self.session.scalar(
            select(Target.target_value)
            .join(Subdomain, Subdomain.target_id == Target.id)
            .where(Subdomain.scan_id == scan_id)
            .limit(1)
        )
        root = registrable_domain(target_value or "")
        if not root:
            return RelatedDomains()

        rows = (
            await self.session.execute(
                select(
                    HttpAsset.host,
                    HttpAsset.tls_subject_cn,
                    HttpAsset.tls_sans,
                    HttpAsset.is_cdn,
                ).where(HttpAsset.scan_id == scan_id)
            )
        ).all()

        certs = []
        for host, subject_cn, sans, is_cdn in rows:
            names = {_clean(str(san)) for san in (sans or [])}
            names.discard("")
            if names:
                certs.append(
                    Cert(
                        host_root=registrable_domain(_clean(host)),
                        cn_root=registrable_domain(_clean(subject_cn) or host),
                        names=names,
                        host=host,
                        fronted=bool(is_cdn),
                    )
                )

        # only trust certificates we own: start at the target root, then let a
        # newly trusted domain vouch for the next one
        trusted = {root}
        for _ in range(_MAX_TRUST_PASSES):
            grown = set(trusted)
            for cert in certs:
                if cert.ours(trusted):
                    grown |= {registrable_domain(name) for name in cert.names}
            grown.discard("")
            if grown == trusted:
                break
            trusted = grown

        known = set(
            (
                await self.session.execute(
                    select(Subdomain.name).where(Subdomain.scan_id == scan_id)
                )
            )
            .scalars()
            .all()
        )
        existing = {
            registrable_domain(value)
            for value in (
                await self.session.execute(
                    select(Target.target_value).where(Target.project_id == project_id)
                )
            )
            .scalars()
            .all()
        }

        hostnames: dict[str, set[str]] = defaultdict(set)
        evidence: dict[str, dict[str, str]] = defaultdict(dict)
        # a hostname is better proof than the address behind it, so it claims the evidence
        for cert in sorted(certs, key=lambda c: not c.host_root):
            if not cert.ours(trusted):
                continue
            host, names = cert.host, cert.names
            for name in names:
                domain = registrable_domain(name)
                if not domain or domain == root or domain in VENDOR_DOMAINS:
                    continue
                if domain.rsplit(".", 1)[-1] in PRIVATE_TLDS:
                    continue
                hostnames[domain].add(name)
                evidence[domain].setdefault(name, host)

        domains = [
            RelatedDomain(
                domain=domain,
                reason=RelatedReason.CERT_SAN.value,
                reason_label=RELATED_REASON_LABELS[RelatedReason.CERT_SAN.value],
                reason_detail=RELATED_REASON_DETAIL[RelatedReason.CERT_SAN.value],
                hostnames=sorted(names)[:MAX_RELATED_HOSTNAMES],
                hostname_count=len(names),
                evidence=[
                    RelatedEvidence(hostname=name, seen_on=evidence[domain][name])
                    for name in sorted(names)[:MAX_RELATED_HOSTNAMES]
                ],
                is_target=domain in existing,
            )
            for domain, names in hostnames.items()
            if not names <= known
        ]
        domains.sort(key=lambda d: (d.is_target, -d.hostname_count, d.domain))
        return RelatedDomains(domains=domains[:MAX_RELATED_DOMAINS], root=root)
