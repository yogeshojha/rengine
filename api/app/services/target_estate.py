"""The estate around one target: domains it points at, providers it runs on, targets it shares with."""

from __future__ import annotations

import ipaddress
import re
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.surface_scope import SurfaceScopeService
from app.services.target_relations import TargetRelationService
from shared.definitions.domains import (
    IGNORED_DOMAINS,
    PRIVATE_TLDS,
    VENDOR_DOMAINS,
    registrable_domain,
    takeover_provider,
)
from shared.definitions.estate import (
    ESTATE_REASON_LABELS,
    ESTATE_REASON_ORDER,
    MAX_ESTATE_DOMAINS,
    MAX_ESTATE_HOSTS,
    MAX_PROJECT_ESTATE,
    NEIGHBOUR_MAX_NAMES,
    PROVIDER_SUFFIXES,
    EstateReason,
    EstateStrength,
    ProviderKind,
)
from shared.definitions.relations import TargetRelation
from shared.definitions.surface import SurfaceDimension
from shared.enums.dns import DnsRecordType
from shared.enums.target import TargetType
from shared.models.dns import DnsRecord
from shared.models.estate import (
    EstateCounts,
    EstateDomain,
    EstateNeighbourCert,
    EstateProvider,
    EstateSignal,
    EstateSource,
    ProjectEstate,
    TargetEstate,
)
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.services.asset_query import lead_cache
from shared.utils.infra import is_shared_nameserver, shared_edge
from shared.utils.net import cert_covers

_EDGE_PROVIDERS = frozenset(
    {
        "Azure Front Door",
        "Azure CDN",
        "Azure Traffic Manager",
        "CloudFront",
        "Cloudflare",
        "Akamai",
        "Fastly",
        "Imperva",
        "Sucuri",
    }
)
_SPF_INCLUDE = re.compile(r"include:([^\s]+)")
_SPF_NETWORK = re.compile(r"ip[46]:([^\s]+)")
_DOMAIN_TYPES = (TargetType.DOMAIN, TargetType.URL)
_SHARED_KINDS = frozenset({EstateReason.ADDRESS.value, TargetRelation.FAVICON.value})


@dataclass
class _Signal:
    hosts: set[str] = field(default_factory=set)
    details: set[str] = field(default_factory=set)
    named: bool = False
    shared: bool = False

    def add(self, host: str, detail: str) -> None:
        self.hosts.add(host)
        self.details.add(detail)
        if not _is_address(host):
            self.named = True


@dataclass
class _Provider:
    count: int = 0
    hosts: set[str] = field(default_factory=set)
    query: str | None = None


def _clean(value: str | None) -> str:
    if not value:
        return ""
    host = value.strip().lower().rstrip(".").removeprefix("*.")
    return host if "." in host and " " not in host else ""


def _is_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _inside(apex: str, root: str) -> bool:
    return bool(root) and (apex == root or apex.endswith(f".{root}"))


def _private(apex: str) -> bool:
    return apex.rsplit(".", 1)[-1] in PRIVATE_TLDS


def _kind_for(provider: str) -> ProviderKind:
    return ProviderKind.EDGE if provider in _EDGE_PROVIDERS else ProviderKind.HOSTING


def _url_host(url: str | None) -> str:
    if not url:
        return ""
    try:
        return _clean(urlsplit(url).hostname or "")
    except ValueError:
        return ""


def provider_of(host: str) -> str | None:
    """The platform a host belongs to, or None when it is an estate's own."""
    name = _clean(host)
    if not name:
        return None
    labels = name.split(".")
    for i in range(len(labels) - 1):
        suffix = ".".join(labels[i:])
        if suffix in PROVIDER_SUFFIXES:
            return PROVIDER_SUFFIXES[suffix]
    edge = shared_edge(name)
    if edge:
        return edge
    apex = registrable_domain(name)
    if apex in VENDOR_DOMAINS:
        return apex
    if is_shared_nameserver(name):
        return apex
    return takeover_provider(name)


class TargetEstateService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.scopes = SurfaceScopeService(session)

    async def for_target(
        self,
        project_id: UUID,
        target_id: UUID,
        scan_id: UUID | None = None,
        *,
        relations: bool = True,
    ) -> TargetEstate:
        targets = await self._targets(project_id)
        target = targets.get(target_id)
        if target is None:
            return TargetEstate(target_id=target_id)
        if scan_id is None:
            covering = await self.scopes.scans_by_target(
                project_id, SurfaceDimension.WEB_ASSETS.value
            )
            scan_id = covering.get(target_id)

        root = registrable_domain(target.target_value)
        apexes = {
            registrable_domain(t.target_value): t.id
            for t in targets.values()
            if registrable_domain(t.target_value)
        }
        signals: dict[str, dict[str, _Signal]] = defaultdict(
            lambda: defaultdict(_Signal)
        )
        providers: dict[tuple[str, str], _Provider] = defaultdict(_Provider)
        neighbours: list[EstateNeighbourCert] = []
        own: list[str] = []

        if scan_id is not None:
            await self._assets(scan_id, root, signals, providers, neighbours)
            await self._cnames(scan_id, root, signals, providers)
        if TargetType(target.target_type) in _DOMAIN_TYPES:
            await self._dns(target_id, root, providers, own)
        if relations:
            await self._relations(project_id, target_id, targets, signals)
            if scan_id is not None:
                await self._addresses(project_id, scan_id, target_id, targets, signals)

        domains = self._domains(signals, apexes, root)
        out = TargetEstate(
            target_id=target_id,
            scan_id=scan_id,
            root=root,
            domains=domains[:MAX_ESTATE_DOMAINS],
            providers=self._providers(providers),
            neighbours=sorted(neighbours, key=lambda n: -n.names),
            own=list(dict.fromkeys(own)),
            considered_targets=len(targets),
        )
        out.counts = EstateCounts(
            untracked=sum(1 for d in domains if d.target_id is None),
            tracked=sum(1 for d in domains if d.target_id is not None),
            providers=len(out.providers),
            neighbour_names=sum(n.names for n in neighbours),
            by_reason=self._by_reason(domains),
        )
        return out

    async def for_project(self, project_id: UUID) -> ProjectEstate:
        covering = await self.scopes.scans_by_target(
            project_id, SurfaceDimension.WEB_ASSETS.value
        )
        if not covering:
            return ProjectEstate()
        return await lead_cache.cached(
            self.session,
            name="project_estate",
            scans=tuple(sorted(covering.values(), key=str)),
            facets=str(project_id),
            model=ProjectEstate,
            build=lambda: self._project(project_id, covering),
        )

    async def _project(
        self, project_id: UUID, covering: dict[UUID, UUID]
    ) -> ProjectEstate:
        targets = await self._targets(project_id)
        merged: dict[str, EstateDomain] = {}
        examined = 0
        for target_id, scan_id in covering.items():
            target = targets.get(target_id)
            if target is None or TargetType(target.target_type) not in _DOMAIN_TYPES:
                continue
            examined += 1
            estate = await self.for_target(
                project_id, target_id, scan_id, relations=False
            )
            for d in estate.domains:
                if d.target_id is not None:
                    continue
                entry = merged.setdefault(d.domain, EstateDomain(domain=d.domain))
                entry.strength = max(entry.strength, d.strength)
                entry.sources.append(
                    EstateSource(
                        target_id=target_id,
                        target_value=target.target_value,
                        scan_id=scan_id,
                    )
                )
                known = {s.kind: s for s in entry.signals}
                for s in d.signals:
                    if s.kind in known:
                        known[s.kind].count += s.count
                        known[s.kind].hosts = (known[s.kind].hosts + s.hosts)[
                            :MAX_ESTATE_HOSTS
                        ]
                    else:
                        entry.signals.append(s.model_copy())
        domains = sorted(
            merged.values(),
            key=lambda d: (-d.strength, -len(d.sources), d.domain),
        )
        return ProjectEstate(
            targets_examined=examined,
            untracked=len(domains),
            domains=domains[:MAX_PROJECT_ESTATE],
        )

    # ---------- readers ----------

    async def _targets(self, project_id: UUID) -> dict[UUID, Target]:
        rows = await self.session.execute(
            select(Target).where(Target.project_id == project_id)
        )
        return {row.id: row for row in rows.scalars().all()}

    async def _assets(
        self,
        scan_id: UUID,
        root: str,
        signals: dict[str, dict[str, _Signal]],
        providers: dict[tuple[str, str], _Provider],
        neighbours: list[EstateNeighbourCert],
    ) -> None:
        rows = (
            await self.session.execute(
                select(
                    HttpAsset.host,
                    HttpAsset.final_url,
                    HttpAsset.location,
                    HttpAsset.tls_subject_cn,
                    HttpAsset.tls_sans,
                ).where(HttpAsset.scan_id == scan_id)
            )
        ).all()
        seen_neighbour: set[str] = set()
        for host, final_url, location, subject_cn, sans in rows:
            for url in (final_url, location):
                self._redirect(host, _url_host(url), root, signals, providers)
            self._certificate(
                host,
                subject_cn,
                sans or [],
                root,
                signals,
                providers,
                neighbours,
                seen_neighbour,
            )

    def _redirect(
        self,
        host: str,
        to: str,
        root: str,
        signals: dict[str, dict[str, _Signal]],
        providers: dict[tuple[str, str], _Provider],
    ) -> None:
        if not to or _is_address(to):
            return
        apex = registrable_domain(to)
        if not apex or apex == root or _private(apex):
            return
        provider = provider_of(to)
        if provider:
            self._provider(providers, provider, _kind_for(provider), host)
            return
        if apex in IGNORED_DOMAINS:
            return
        signals[apex][EstateReason.REDIRECT.value].add(host, to)

    def _certificate(
        self,
        host: str,
        subject_cn: str | None,
        sans: list,
        root: str,
        signals: dict[str, dict[str, _Signal]],
        providers: dict[tuple[str, str], _Provider],
        neighbours: list[EstateNeighbourCert],
        seen_neighbour: set[str],
    ) -> None:
        names = {_clean(str(s)) for s in sans}
        names.discard("")
        subject = _clean(subject_cn)
        subject_apex = registrable_domain(subject) if subject else ""
        apexes = {registrable_domain(n) for n in names}
        apexes.discard("")
        if subject_apex and subject_apex != root and len(apexes) > NEIGHBOUR_MAX_NAMES:
            key = f"{host}:{subject}"
            if key not in seen_neighbour:
                seen_neighbour.add(key)
                neighbours.append(
                    EstateNeighbourCert(
                        host=host,
                        subject=subject,
                        names=len(apexes - {root}),
                        provider=provider_of(subject),
                    )
                )
            return
        if subject_apex and subject_apex != root and not _private(subject_apex):
            provider = provider_of(subject)
            if provider:
                self._provider(providers, provider, _kind_for(provider), host)
            elif subject_apex not in IGNORED_DOMAINS:
                signals[subject_apex][EstateReason.CERT_SUBJECT.value].add(
                    host, subject
                )
        ours = subject_apex == root or cert_covers(host, subject_cn, sans)
        if not ours:
            return
        for name in names:
            apex = registrable_domain(name)
            if (
                not apex
                or apex in (root, subject_apex)
                or _private(apex)
                or apex in IGNORED_DOMAINS
                or provider_of(name)
            ):
                continue
            signals[apex][EstateReason.CERT_SAN.value].add(host, name)

    async def _cnames(
        self,
        scan_id: UUID,
        root: str,
        signals: dict[str, dict[str, _Signal]],
        providers: dict[tuple[str, str], _Provider],
    ) -> None:
        rows = (
            await self.session.execute(
                select(Subdomain.name, Subdomain.cname).where(
                    Subdomain.scan_id == scan_id, Subdomain.cname.isnot(None)
                )
            )
        ).all()
        for name, cname in rows:
            to = _clean(cname)
            apex = registrable_domain(to)
            if not to or not apex or apex == root or _private(apex):
                continue
            provider = provider_of(to)
            if provider:
                kind = _kind_for(provider)
                suffix = next(
                    (s for s in PROVIDER_SUFFIXES if to == s or to.endswith(f".{s}")),
                    apex,
                )
                self._provider(providers, provider, kind, name, query=f"cname:{suffix}")
                continue
            if apex in IGNORED_DOMAINS:
                continue
            signals[apex][EstateReason.CNAME.value].add(name, to)

    async def _dns(
        self,
        target_id: UUID,
        root: str,
        providers: dict[tuple[str, str], _Provider],
        own: list[str],
    ) -> None:
        rows = (
            await self.session.execute(
                select(DnsRecord.record_type, DnsRecord.value).where(
                    DnsRecord.target_id == target_id,
                    DnsRecord.record_type.in_(
                        [DnsRecordType.NS, DnsRecordType.MX, DnsRecordType.TXT]
                    ),
                )
            )
        ).all()
        for kind, value in rows:
            record = str(kind).upper().removeprefix("DNSRECORDTYPE.")
            host = _clean(value)
            if record in ("NS", "MX"):
                if not host:
                    continue
                apex = registrable_domain(host)
                if apex == root:
                    own.append(host)
                    continue
                name = provider_of(host) or apex
                role = ProviderKind.DNS if record == "NS" else ProviderKind.MAIL
                self._provider(providers, name, role, host)
            elif record == "TXT" and (value or "").lower().startswith("v=spf1"):
                for m in _SPF_INCLUDE.finditer(value.lower()):
                    include = _clean(m.group(1))
                    if not include:
                        continue
                    if registrable_domain(include) == root:
                        own.append(include)
                        continue
                    name = provider_of(include) or registrable_domain(include)
                    self._provider(providers, name, ProviderKind.MAIL, include)
                for m in _SPF_NETWORK.finditer(value.lower()):
                    own.append(m.group(1))

    async def _relations(
        self,
        project_id: UUID,
        target_id: UUID,
        targets: dict[UUID, Target],
        signals: dict[str, dict[str, _Signal]],
    ) -> None:
        related = await TargetRelationService(self.session).for_target(
            project_id, target_id
        )
        for item in related.items:
            other = targets.get(item.target_id)
            if other is None:
                continue
            apex = registrable_domain(other.target_value) or other.target_value
            for reason in item.reasons:
                sig = signals[apex][reason.kind]
                sig.details.add(reason.detail or reason.value)
                sig.named = True
                if reason.kind == TargetRelation.CERTIFICATE.value and provider_of(
                    reason.detail
                ):
                    sig.shared = True

    async def _addresses(
        self,
        project_id: UUID,
        scan_id: UUID,
        target_id: UUID,
        targets: dict[UUID, Target],
        signals: dict[str, dict[str, _Signal]],
    ) -> None:
        covering = await self.scopes.scans_by_target(
            project_id, SurfaceDimension.WEB_ASSETS.value
        )
        others = [sid for tid, sid in covering.items() if tid != target_id]
        if not others:
            return
        a = HttpAsset
        b = HttpAsset.__table__.alias("b")
        rows = (
            await self.session.execute(
                select(
                    b.c.target_id,
                    func.count(func.distinct(a.ip)),
                    func.min(a.host),
                    func.min(a.ip),
                )
                .select_from(a)
                .join(b, b.c.ip == a.ip)
                .where(
                    a.scan_id == scan_id,
                    a.ip.isnot(None),
                    a.is_cdn.is_(False),
                    b.c.scan_id.in_(others),
                    b.c.is_cdn.is_(False),
                )
                .group_by(b.c.target_id)
            )
        ).all()
        for other_id, count, host, ip in rows:
            other = targets.get(other_id)
            if other is None:
                continue
            apex = registrable_domain(other.target_value) or other.target_value
            sig = signals[apex][EstateReason.ADDRESS.value]
            sig.add(host, f"{count} shared, {ip}" if count > 1 else ip)
            sig.shared = True

    # ---------- shaping ----------

    @staticmethod
    def _provider(
        providers: dict[tuple[str, str], _Provider],
        name: str,
        kind: ProviderKind,
        host: str,
        query: str | None = None,
    ) -> None:
        entry = providers[(name, kind.value)]
        entry.count += 1
        entry.hosts.add(host)
        if query and entry.query is None:
            entry.query = query

    @staticmethod
    def _providers(providers: dict[tuple[str, str], _Provider]) -> list[EstateProvider]:
        out = [
            EstateProvider(
                name=name,
                kind=kind,
                count=entry.count,
                detail=", ".join(sorted(entry.hosts)[:MAX_ESTATE_HOSTS]),
                query=entry.query,
            )
            for (name, kind), entry in providers.items()
        ]
        out.sort(key=lambda p: (-p.count, p.name))
        return out

    @staticmethod
    def _domains(
        signals: dict[str, dict[str, _Signal]],
        apexes: dict[str, UUID],
        root: str,
    ) -> list[EstateDomain]:
        out: list[EstateDomain] = []
        for apex, kinds in signals.items():
            if _inside(apex, root):
                continue
            ordered = sorted(
                kinds.items(),
                key=lambda kv: (
                    ESTATE_REASON_ORDER.index(kv[0])
                    if kv[0] in ESTATE_REASON_ORDER
                    else len(ESTATE_REASON_ORDER)
                ),
            )
            rows = [
                EstateSignal(
                    kind=kind,
                    label=ESTATE_REASON_LABELS.get(kind, kind),
                    strength=(
                        EstateStrength.SHARED.value
                        if kind in _SHARED_KINDS or sig.shared or not sig.named
                        else EstateStrength.DIRECT.value
                    ),
                    detail=", ".join(sorted(sig.details)[:MAX_ESTATE_HOSTS]),
                    hosts=sorted(sig.hosts)[:MAX_ESTATE_HOSTS],
                    count=max(len(sig.hosts), len(sig.details)),
                )
                for kind, sig in ordered
            ]
            out.append(
                EstateDomain(
                    domain=apex,
                    target_id=apexes.get(apex),
                    strength=sum(
                        1 for r in rows if r.strength == EstateStrength.DIRECT.value
                    ),
                    signals=rows,
                )
            )
        out.sort(key=lambda d: (-d.strength, d.target_id is not None, d.domain))
        return out

    @staticmethod
    def _by_reason(domains: list[EstateDomain]) -> dict[str, int]:
        tally: dict[str, int] = defaultdict(int)
        for d in domains:
            for s in d.signals:
                tally[s.kind] += 1
        return dict(tally)
