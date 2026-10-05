"""The estate around one target: domains it points at, providers it runs on, targets it shares with."""

from __future__ import annotations

import uuid as uuid_module
from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.program_coverage import ProgramCoverageService
from app.services.surface_scope import SurfaceScopeService
from app.services.target_relations import TargetRelationService
from shared.definitions.domains import (
    IGNORED_DOMAINS,
    PRIVATE_TLDS,
    is_public_tld,
    owning_zone,
    registrable_domain,
    target_zone,
)
from shared.definitions.estate import (
    EDGE_PROVIDERS,
    ESTATE_REASON_LABELS,
    ESTATE_REASON_ORDER,
    MAX_ESTATE_DOMAINS,
    MAX_ESTATE_HOSTS,
    MAX_PROJECT_ESTATE,
    NEIGHBOUR_MAX_NAMES,
    PROVIDER_SUFFIXES,
    EstateReason,
    EstateStrength,
    EstateTriageState,
    ProviderKind,
    provider_of,
)
from shared.definitions.infostealer import APP_ID_HEADS, MIN_BRAND_LENGTH
from shared.definitions.name_ownership import CLAIM_TEMPLATES
from shared.definitions.relations import TargetRelation
from shared.definitions.surface import SurfaceDimension
from shared.enums.dns import DnsRecordType
from shared.enums.target import HOSTNAME_TARGET_TYPES, TargetType
from shared.models.dns import DnsRecord
from shared.models.estate import (
    EstateCandidate,
    EstateCounts,
    EstateDomain,
    EstateDossier,
    EstateNeighbourCert,
    EstateProvider,
    EstateSignal,
    EstateSource,
    EstateTriage,
    ProjectEstate,
    TargetEstate,
)
from shared.models.http_asset import HttpAsset
from shared.models.infostealer import TargetInfostealer
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import lead_cache
from shared.services.domain_posture import spf
from shared.utils.datetime import utc_now
from shared.utils.net import cert_covers, url_host
from shared.utils.text import counted
from shared.utils.validation import validate_ip

_SHARED_KINDS = frozenset({EstateReason.ADDRESS.value, TargetRelation.FAVICON.value})


@dataclass
class _Signal:
    hosts: set[str] = field(default_factory=set)
    details: set[str] = field(default_factory=set)
    named: bool = False
    shared: bool = False
    total: int = 0

    def add(self, host: str, detail: str) -> None:
        self.hosts.add(host)
        self.details.add(detail)
        if not validate_ip(host):
            self.named = True


@dataclass
class _Cert:
    """What one certificate says, whichever host presents it."""

    subject: str
    subject_inside: bool
    neighbour: EstateNeighbourCert | None = None
    provider: str | None = None
    subject_apex: str | None = None
    sans: list[tuple[str, str]] = field(default_factory=list)


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


def _inside(apex: str, root: str) -> bool:
    return bool(root) and (apex == root or apex.endswith(f".{root}"))


def _private(apex: str) -> bool:
    return apex.rsplit(".", 1)[-1] in PRIVATE_TLDS


def _credentials(domain: EstateDomain) -> int:
    return sum(
        s.count for s in domain.signals if s.kind == EstateReason.EMPLOYEE_LOGINS.value
    )


def _kind_for(provider: str) -> ProviderKind:
    return ProviderKind.EDGE if provider in EDGE_PROVIDERS else ProviderKind.HOSTING


def _service_domain(name: object, root: str) -> str:
    """The registrable domain of an infostealer third-party service, or empty."""
    host = _clean(name if isinstance(name, str) else None)
    if not host or validate_ip(host) or host.split(".", 1)[0] in APP_ID_HEADS:
        return ""
    apex = registrable_domain(host)
    if (
        not apex
        or _inside(apex, root)
        or _private(apex)
        or not is_public_tld(apex)
        or apex in IGNORED_DOMAINS
        or provider_of(host)
    ):
        return ""
    return apex


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
        dismissed: set[str] | None = None,
        with_programs: bool = False,
        persist: bool = False,
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

        root = target_zone(target.target_value)
        apexes = {target_zone(t.target_value): t.id for t in targets.values()}
        signals: dict[str, dict[str, _Signal]] = defaultdict(
            lambda: defaultdict(_Signal)
        )
        providers: dict[tuple[str, str], _Provider] = defaultdict(_Provider)
        neighbours: list[EstateNeighbourCert] = []

        if scan_id is not None:
            await self._assets(scan_id, root, signals, providers, neighbours)
            await self._cnames(scan_id, root, signals, providers)
            await self._drop_claimed(scan_id, signals)
        if TargetType(target.target_type) in HOSTNAME_TARGET_TYPES:
            nameservers = await self._dns(target_id, root, providers)
            await self._infostealer(target_id, root, nameservers, signals)
        if relations:
            await self._relations(project_id, target_id, targets, signals)
            if scan_id is not None:
                await self._addresses(project_id, scan_id, target_id, targets, signals)

        domains = self._domains(signals, apexes, root)
        if dismissed is None:
            dismissed = await self._dismissed(project_id)
        for d in domains:
            if d.target_id is None and d.domain in dismissed:
                d.state = EstateTriageState.DISMISSED.value
        open_domains = [d for d in domains if d.state == EstateTriageState.OPEN.value]
        closed = [d for d in domains if d.state != EstateTriageState.OPEN.value]
        shown = (open_domains + closed)[:MAX_ESTATE_DOMAINS]
        if with_programs:
            await self._attach_programs(shown)
        await self._attach_dossier(project_id, shown)
        if persist:
            await self._persist_candidates(
                project_id,
                [d.domain for d in open_domains if d.target_id is None],
            )
        return TargetEstate(
            target_id=target_id,
            scan_id=scan_id,
            root=root,
            counts=EstateCounts(
                untracked=sum(1 for d in open_domains if d.target_id is None)
            ),
            domains=shown,
            providers=self._providers(providers),
            neighbours=sorted(neighbours, key=lambda n: -n.names),
        )

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
        dismissed = await self._dismissed(project_id)
        merged: dict[str, EstateDomain] = {}
        examined = 0
        for target_id, scan_id in covering.items():
            target = targets.get(target_id)
            if (
                target is None
                or TargetType(target.target_type) not in HOSTNAME_TARGET_TYPES
            ):
                continue
            examined += 1
            estate = await self.for_target(
                project_id, target_id, scan_id, relations=False, dismissed=dismissed
            )
            for d in estate.domains:
                if d.target_id is not None:
                    continue
                entry = merged.setdefault(
                    d.domain, EstateDomain(domain=d.domain, state=d.state)
                )
                entry.strength = max(entry.strength, d.strength)
                if entry.dossier is None:
                    entry.dossier = d.dossier
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
            key=lambda d: (
                d.state != EstateTriageState.OPEN.value,
                -d.strength,
                -len(d.sources),
                -_credentials(d),
                d.domain,
            ),
        )
        open_count = sum(1 for d in domains if d.state == EstateTriageState.OPEN.value)
        shown = domains[:MAX_PROJECT_ESTATE]
        await self._persist_candidates(
            project_id,
            [d.domain for d in shown if d.state == EstateTriageState.OPEN.value],
        )
        return ProjectEstate(
            targets_examined=examined,
            untracked=open_count,
            domains=shown,
        )

    async def _attach_programs(self, domains: list[EstateDomain]) -> None:
        candidates = [
            d
            for d in domains
            if d.target_id is None and d.state == EstateTriageState.OPEN.value
        ]
        if not candidates:
            return
        matches = await ProgramCoverageService(self.session).best_for_hosts(
            {d.domain for d in candidates}
        )
        for d in candidates:
            d.program = matches.get(d.domain)

    async def _attach_dossier(
        self, project_id: UUID, domains: list[EstateDomain]
    ) -> None:
        names = [d.domain for d in domains if d.target_id is None]
        if not names:
            return
        rows = (
            await self.session.execute(
                select(EstateCandidate).where(
                    EstateCandidate.project_id == project_id,
                    EstateCandidate.domain.in_(names),
                    EstateCandidate.checked_at.isnot(None),
                )
            )
        ).scalars()
        by_domain = {r.domain: r for r in rows}
        for d in domains:
            row = by_domain.get(d.domain)
            if row is None:
                continue
            d.dossier = EstateDossier(
                resolves=row.resolves,
                ports=list(row.ports),
                registered_at=row.registered_at,
                registrar=row.registrar,
                takeover_provider=row.takeover_provider,
                checked_at=row.checked_at,
            )

    async def _persist_candidates(self, project_id: UUID, names: list[str]) -> None:
        clean = sorted({_clean(n) for n in names} - {""})
        if not clean:
            return
        now = utc_now()
        stmt = insert(EstateCandidate).values(
            [
                {
                    "id": uuid_module.uuid4(),
                    "project_id": project_id,
                    "domain": domain,
                    "a": [],
                    "aaaa": [],
                    "ports": [],
                    "updated_at": now,
                }
                for domain in clean
            ]
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_estate_candidate_project_domain"
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def triage(self, project_id: UUID, domains: list[str], state: str) -> int:
        clean = sorted({_clean(d) for d in domains} - {""})
        if not clean:
            return 0
        now = utc_now()
        stmt = insert(EstateTriage).values(
            [
                {
                    "id": uuid_module.uuid4(),
                    "project_id": project_id,
                    "domain": domain,
                    "state": state,
                    "updated_at": now,
                }
                for domain in clean
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_estate_triage_project_domain",
            set_={"state": stmt.excluded.state, "updated_at": stmt.excluded.updated_at},
        )
        await self.session.execute(stmt)
        await self.session.commit()
        target_ids = (
            await self.session.execute(
                select(Target.id).where(Target.project_id == project_id)
            )
        ).scalars()
        await lead_cache.bump(list(target_ids))
        return len(clean)

    # ---------- readers ----------

    async def _dismissed(self, project_id: UUID) -> set[str]:
        rows = await self.session.execute(
            select(EstateTriage.domain).where(
                EstateTriage.project_id == project_id,
                EstateTriage.state == EstateTriageState.DISMISSED.value,
            )
        )
        return set(rows.scalars())

    async def _drop_claimed(
        self, scan_id: UUID, signals: dict[str, dict[str, _Signal]]
    ) -> None:
        claimed = (
            await self.session.execute(
                select(Vulnerability.matcher_name)
                .where(
                    Vulnerability.scan_id == scan_id,
                    Vulnerability.template_id.in_(list(CLAIM_TEMPLATES.values())),
                )
                .distinct()
            )
        ).scalars()
        for domain in claimed:
            signals.pop(domain or "", None)

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
        redirects: dict[str | None, tuple | None] = {}
        certificates: dict[tuple, _Cert] = {}
        for host, final_url, location, subject_cn, sans in rows:
            for url in (final_url, location):
                if url not in redirects:
                    redirects[url] = self._redirect(_clean(url_host(url)), root)
                self._apply_redirect(host, redirects[url], signals, providers)
            raw = sans or []
            key = (subject_cn, tuple(str(s) for s in raw))
            cert = certificates.get(key)
            if cert is None:
                cert = certificates[key] = self._certificate(subject_cn, raw, root)
            self._apply_certificate(
                host,
                cert,
                subject_cn,
                raw,
                signals,
                providers,
                neighbours,
                seen_neighbour,
            )

    @staticmethod
    def _redirect(to: str, root: str) -> tuple | None:
        """Where a redirect lands: a provider, a domain or nothing."""
        if not to or validate_ip(to):
            return None
        apex = registrable_domain(to)
        if not apex or _inside(apex, root) or _private(apex):
            return None
        provider = provider_of(to)
        if provider:
            return (provider, None, None)
        if apex in IGNORED_DOMAINS:
            return None
        return (None, apex, to)

    def _apply_redirect(
        self,
        host: str,
        landing: tuple | None,
        signals: dict[str, dict[str, _Signal]],
        providers: dict[tuple[str, str], _Provider],
    ) -> None:
        if landing is None:
            return
        provider, apex, to = landing
        if provider:
            self._provider(providers, provider, _kind_for(provider), host)
            return
        signals[apex][EstateReason.REDIRECT.value].add(host, to)

    @staticmethod
    def _certificate(subject_cn: str | None, sans: list, root: str) -> _Cert:
        names = {_clean(str(s)) for s in sans}
        names.discard("")
        subject = _clean(subject_cn)
        subject_apex = registrable_domain(subject) if subject else ""
        apexes = {registrable_domain(n) for n in names}
        apexes.discard("")
        outside = bool(subject_apex) and not _inside(subject_apex, root)
        cert = _Cert(subject=subject, subject_inside=_inside(subject_apex, root))
        if outside and len(apexes) > NEIGHBOUR_MAX_NAMES:
            cert.neighbour = EstateNeighbourCert(
                host="",
                subject=subject,
                names=sum(1 for a in apexes if not _inside(a, root)),
                provider=provider_of(subject),
            )
            return cert
        if outside and not _private(subject_apex):
            provider = provider_of(subject)
            if provider:
                cert.provider = provider
            elif subject_apex not in IGNORED_DOMAINS:
                cert.subject_apex = subject_apex
        for name in names:
            apex = registrable_domain(name)
            if (
                not apex
                or _inside(apex, root)
                or apex == subject_apex
                or _private(apex)
                or apex in IGNORED_DOMAINS
                or provider_of(name)
            ):
                continue
            cert.sans.append((apex, name))
        return cert

    def _apply_certificate(
        self,
        host: str,
        cert: _Cert,
        subject_cn: str | None,
        sans: list,
        signals: dict[str, dict[str, _Signal]],
        providers: dict[tuple[str, str], _Provider],
        neighbours: list[EstateNeighbourCert],
        seen_neighbour: set[str],
    ) -> None:
        if cert.neighbour is not None:
            key = f"{host}:{cert.subject}"
            if key not in seen_neighbour:
                seen_neighbour.add(key)
                neighbours.append(cert.neighbour.model_copy(update={"host": host}))
            return
        if cert.provider:
            self._provider(providers, cert.provider, _kind_for(cert.provider), host)
        elif cert.subject_apex:
            signals[cert.subject_apex][EstateReason.CERT_SUBJECT.value].add(
                host, cert.subject
            )
        if not (cert.subject_inside or cert_covers(host, subject_cn, sans)):
            return
        for apex, name in cert.sans:
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
            if not to or not apex or _inside(apex, root) or _private(apex):
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
    ) -> dict[str, str]:
        nameservers: dict[str, str] = {}
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
            host = _clean(value)
            if kind in (DnsRecordType.NS, DnsRecordType.MX):
                if not host:
                    continue
                apex = registrable_domain(host)
                if _inside(apex, root):
                    continue
                provider = provider_of(host)
                role = (
                    ProviderKind.DNS if kind is DnsRecordType.NS else ProviderKind.MAIL
                )
                self._provider(providers, provider or apex, role, host)
                if kind is DnsRecordType.NS and not provider and apex:
                    nameservers.setdefault(apex, host)
            elif kind is DnsRecordType.TXT and value and spf.is_spf(value):
                for zone in spf.include_zones(value):
                    include = _clean(zone)
                    if not include:
                        continue
                    if _inside(registrable_domain(include), root):
                        continue
                    name = provider_of(include) or registrable_domain(include)
                    self._provider(providers, name, ProviderKind.MAIL, include)
        return nameservers

    async def _infostealer(
        self,
        target_id: UUID,
        root: str,
        nameservers: dict[str, str],
        signals: dict[str, dict[str, _Signal]],
    ) -> None:
        services = (
            await self.session.execute(
                select(TargetInfostealer.services).where(
                    TargetInfostealer.target_id == target_id
                )
            )
        ).scalar_one_or_none()
        credentials: dict[str, int] = defaultdict(int)
        for row in services or []:
            if not isinstance(row, dict):
                continue
            apex = _service_domain(row.get("name"), root)
            if apex:
                count = row.get("count")
                credentials[apex] += count if isinstance(count, int) else 0
        brand = root.split(".", 1)[0]
        if len(brand) < MIN_BRAND_LENGTH:
            brand = ""
        for apex, count in credentials.items():
            logins = signals[apex][EstateReason.EMPLOYEE_LOGINS.value]
            if count > 0:
                logins.details.add(counted(count, "credential"))
            logins.named = True
            logins.shared = True
            logins.total += count
            if brand and brand in apex.split(".", 1)[0]:
                tie = signals[apex][EstateReason.NAME.value]
                tie.details.add(brand)
                tie.named = True
            if apex in nameservers:
                tie = signals[apex][TargetRelation.NAMESERVER.value]
                tie.details.add(nameservers[apex])
                tie.named = True

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
            apex = target_zone(other.target_value)
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
            apex = target_zone(other.target_value)
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
                    count=sig.total or max(len(sig.hosts), len(sig.details)),
                )
                for kind, sig in ordered
            ]
            out.append(
                EstateDomain(
                    domain=apex,
                    target_id=apexes.get(owning_zone(apex, apexes) or ""),
                    strength=sum(
                        1 for r in rows if r.strength == EstateStrength.DIRECT.value
                    ),
                    signals=rows,
                )
            )
        out.sort(
            key=lambda d: (
                -d.strength,
                d.target_id is not None,
                -_credentials(d),
                d.domain,
            )
        )
        return out
