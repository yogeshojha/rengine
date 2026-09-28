"""Domains and networks registered to an organization, across keyless sources."""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from pydantic import Field

from shared.definitions.domains import registrable_domain
from shared.definitions.toolbox import (
    MAX_INPUT_LENGTH,
    RowAction,
    Tone,
    ToolExecution,
    ToolGroup,
)
from shared.logging import get_logger
from shared.utils.net import cert_covers
from shared.utils.privacy import is_redacted_name
from toolbox import estate, org_lookup
from toolbox.base import (
    Tool,
    ToolContext,
    ToolError,
    ToolInput,
    ToolOutcome,
    cell,
    fact,
    facts,
    glyph,
    hero,
    lookup,
    mark,
    metric,
    table,
    tag,
    tags,
)
from toolbox.org_lookup import (
    EVIDENCE_LABELS,
    MAX_DOMAINS,
    MAX_NETWORKS,
    MAX_SIMILAR,
    DomainFacts,
    Evidence,
    InputKind,
    InputRefusedError,
    Query,
)
from toolbox.pivot import target_pivot
from tools.crtsh.client import CrtShClient, CrtShError
from tools.crtsh.models import CrtShOrganization
from tools.ripestat.models import SearchASN
from tools.ripestat.service import RIPEStatLookupError, RIPEStatService
from tools.viewdns.client import ViewDNSRejectedError
from tools.viewdns.models import ReverseWhoisResponse
from tools.viewdns.service import (
    ViewDNSKeyNotConfiguredError,
    ViewDNSLookupError,
    ViewDNSService,
)
from tools.whois.service import WhoisError, WhoisService

logger = get_logger(__name__)

WHOIS_TIMEOUT = 12
NOT_FOR_EMAIL = "Not used for an email address"

_CERTIFICATES = "Certificate transparency"
_REGISTRATIONS = "Reverse WHOIS"
_NETWORKS = "Routing registry"


class Input(ToolInput):
    organization: str = Field(
        ...,
        max_length=MAX_INPUT_LENGTH,
        title="Organization, domain or registrant email",
        description="Cloudflare, Inc. · github.com · hostmaster@example.com",
    )


@dataclass
class Owner:
    name: str
    source: str
    certificates: int = 0


@dataclass
class Sources:
    certificates: str = ""
    registrations: str = ""
    networks: str = ""
    answered: int = 0
    certificate_domains: dict[str, date | None] = field(default_factory=dict)
    registrations_found: dict[str, tuple[date | None, str]] = field(
        default_factory=dict
    )
    similar: list[CrtShOrganization] = field(default_factory=list)
    networks_found: list[SearchASN] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)


class OrgDomains(Tool):
    name = "org_domains"
    title = "Domains by organization"
    description = (
        "Domains and networks registered to an organization, from certificate "
        "transparency, reverse WHOIS and the routing registry."
    )
    group = ToolGroup.INTEL.value
    icon = "building-2"
    execution = ToolExecution.INLINE.value
    order = 20
    value_field = "organization"
    command = "org"
    placeholder = "Cloudflare, Inc. or github.com"
    examples = ("Cloudflare, Inc.", "github.com", "O'Reilly Media")
    Input = Input

    async def run(self, ctx: ToolContext, args: Input) -> ToolOutcome:
        try:
            query = org_lookup.read(args.organization)
        except InputRefusedError as exc:
            raise ToolError(str(exc)) from exc

        owner = await self._owner(ctx, query)
        sources = Sources()
        await asyncio.gather(
            self._certificates(owner, sources),
            self._networks(owner, sources),
            self._registrations(ctx, query, owner, sources),
        )
        if not sources.answered:
            msg = "No source answered. Try again in a minute."
            raise ToolError(msg)

        merged = org_lookup.merge(
            sources.certificate_domains, sources.registrations_found
        )
        if query.kind == InputKind.DOMAIN:
            evidence = (
                Evidence.CERTIFICATE.value
                if owner and owner.certificates
                else Evidence.REGISTRATION.value
            )
            merged.setdefault(query.value, DomainFacts()).evidence.add(evidence)

        names = sorted(merged)
        truncated = len(names) > MAX_DOMAINS
        names = names[:MAX_DOMAINS]
        found = await estate.classify_domains(ctx.session, ctx.project_id, names)
        targets = set(found.targets)
        names.sort(key=lambda n: org_lookup.rank(n, merged[n], targets, found.seen))
        new = sum(1 for n in names if n not in targets and n not in found.seen)
        tracked = sum(1 for n in names if n in targets)

        caveats = list(dict.fromkeys(sources.caveats))
        if truncated:
            caveats.append(f"Showing {MAX_DOMAINS:,} of {len(merged):,} domains.")

        label = owner.name if owner else query.value
        blocks = [
            _hero(label, query, owner, len(names), new, tracked, sources),
            facts(
                fact(_CERTIFICATES, sources.certificates),
                fact(_REGISTRATIONS, sources.registrations),
                fact(_NETWORKS, sources.networks),
                title="Sources",
            ),
            table(
                ["Domain", "Evidence", "Registered", "Last certificate", "Status"],
                [_row(n, merged[n], found) for n in names],
                title="Domains",
                total=len(names),
                empty="No domains found.",
                action=RowAction.ADD_TARGETS.value,
                keys=[None if n in targets else n for n in names],
            ),
        ]
        if sources.networks_found:
            blocks.append(_networks_block(sources.networks_found))
        if sources.similar:
            blocks.append(_similar_block(sources.similar))

        return ToolOutcome(
            summary=_summary(label, len(names), new, len(sources.networks_found)),
            blocks=blocks,
            caveats=caveats,
            pivot=await target_pivot(ctx, query.value)
            if query.kind == InputKind.DOMAIN
            else None,
            raw={
                "input": query.value,
                "kind": query.kind.value,
                "organization": owner.name if owner else None,
                "owner_source": owner.source if owner else None,
                "domains": [
                    {
                        "domain": n,
                        "evidence": sorted(merged[n].evidence),
                        "registered": _iso(merged[n].registered),
                        "last_certificate": _iso(merged[n].last_certificate),
                        "target_id": str(found.targets[n])
                        if n in found.targets
                        else None,
                    }
                    for n in names
                ],
                "networks": [
                    {"asn": a.asn, "holder": a.holder} for a in sources.networks_found
                ],
            },
        )

    async def _owner(self, ctx: ToolContext, query: Query) -> Owner | None:
        if query.kind == InputKind.ORGANIZATION:
            return Owner(name=query.value, source="input")
        if query.kind == InputKind.EMAIL:
            return None

        rows = await estate.certificates(ctx.session, ctx.project_id, query.value)
        named: Counter[str] = Counter()
        for host, cn, sans, dn in rows:
            organization = org_lookup.subject_organization(dn)
            if organization and cert_covers(host, cn, sans):
                named[organization] += 1
        if named:
            name, count = named.most_common(1)[0]
            return Owner(name=name, source="certificates", certificates=count)

        registrant = await self._registrant(ctx, query.value)
        if registrant:
            return Owner(name=registrant, source="whois")
        msg = (
            f"The owner of {query.value} is not published. Its WHOIS registrant is "
            "redacted and no scan in this project has read a certificate naming "
            "an organization. Enter the organization name."
        )
        raise ToolError(msg)

    async def _registrant(self, ctx: ToolContext, domain: str) -> str:
        service = WhoisService()
        try:
            service.ensure_ready()
            result = await asyncio.wait_for(
                service.lookup(query=domain, store_in_db=True, session=ctx.session),
                timeout=WHOIS_TIMEOUT,
            )
        except (WhoisError, TimeoutError) as exc:
            logger.warning("org_domains whois failed", domain=domain, error=str(exc))
            return ""
        for entity in result.response.entities.registrant:
            name = (entity.name or "").strip()
            if name and not is_redacted_name(name) and org_lookup.org_key(name):
                return name
        return ""

    async def _certificates(self, owner: Owner | None, sources: Sources) -> None:
        if owner is None:
            sources.certificates = NOT_FOR_EMAIL
            return
        variants = list(dict.fromkeys([owner.name, org_lookup.fold(owner.name)]))
        variants = [v for v in variants if v.strip()]
        results = await asyncio.gather(
            *(CrtShClient().search_organization(v) for v in variants),
            return_exceptions=True,
        )
        answers = [r for r in results if not isinstance(r, BaseException)]
        if not answers:
            error = next(r for r in results if isinstance(r, BaseException))
            reason = str(error) if isinstance(error, CrtShError) else "crt.sh failed."
            logger.warning("org_domains crt.sh failed", error=reason)
            sources.certificates = reason
            return

        sources.answered += 1
        key = org_lookup.org_key(owner.name)
        matched: dict[str, CrtShOrganization] = {}
        similar: dict[str, CrtShOrganization] = {}
        certs = 0
        for answer in answers:
            certs = max(certs, answer.certs)
            if answer.stored_at:
                sources.caveats.append(
                    "Certificate transparency answered from a result stored at "
                    f"{answer.stored_at:%Y-%m-%d %H:%M} UTC."
                )
            if answer.capped:
                sources.caveats.append(
                    "crt.sh returned its limit of 10,000 certificates. "
                    "Older certificates are not included."
                )
            for organization in answer.organizations:
                bucket = (
                    matched if org_lookup.org_key(organization.name) == key else similar
                )
                bucket.setdefault(organization.name, organization)

        for organization in matched.values():
            for domain, issued in organization.domains.items():
                current = sources.certificate_domains.get(domain)
                if domain not in sources.certificate_domains or (
                    issued and (current is None or issued > current)
                ):
                    sources.certificate_domains[domain] = issued

        named = sum(o.certs for o in matched.values())
        count = len(sources.certificate_domains)
        sources.certificates = (
            f"crt.sh · {named:,} certificate{'s' if named != 1 else ''} naming this "
            f"organization · {count:,} domain{'s' if count != 1 else ''}"
            if named
            else f"crt.sh · no certificate names this organization · {certs:,} "
            "name a similar one"
            if certs
            else "crt.sh · no certificate names this organization"
        )
        sources.similar = sorted(
            (o for o in similar.values() if org_lookup.org_key(o.name)),
            key=lambda o: (-o.certs, o.name),
        )[:MAX_SIMILAR]

    async def _registrations(
        self, ctx: ToolContext, query: Query, owner: Owner | None, sources: Sources
    ) -> None:
        term = query.value if query.kind == InputKind.EMAIL else owner.name
        try:
            read = await ViewDNSService(ctx.session).reverse_whois(term)
        except ViewDNSKeyNotConfiguredError:
            sources.registrations = "Not queried. Add a ViewDNS.info key in Settings."
            return
        except ViewDNSLookupError as exc:
            logger.warning("org_domains viewdns failed", error=str(exc))
            sources.registrations = (
                "ViewDNS refused this name. Try the full registered name."
                if isinstance(exc.__cause__, ViewDNSRejectedError)
                else "ViewDNS did not answer."
            )
            return

        sources.answered += 1
        response = read.data if read else None
        matches = response.matches if isinstance(response, ReverseWhoisResponse) else []
        for match in matches:
            domain = registrable_domain(match.domain)
            if domain:
                sources.registrations_found.setdefault(
                    domain, (match.created_date, match.registrar)
                )
        count = len(sources.registrations_found)
        sources.registrations = (
            f"ViewDNS · {count:,} domain{'s' if count != 1 else ''}"
            if count
            else "ViewDNS · no registration names this registrant"
        )
        if count:
            sources.caveats.append(
                "Registration matches come from the registrant name and are not "
                "checked against a certificate."
            )
        if read and read.cached and read.queried_at:
            sources.caveats.append(
                f"Reverse WHOIS answered from a result stored on "
                f"{read.queried_at.date().isoformat()}."
            )

    async def _networks(self, owner: Owner | None, sources: Sources) -> None:
        if owner is None:
            sources.networks = NOT_FOR_EMAIL
            return
        terms = [
            t
            for t in dict.fromkeys([owner.name, org_lookup.lead_word(owner.name)])
            if t
        ]
        results = await asyncio.gather(
            *(RIPEStatService().search_asns(t) for t in terms),
            return_exceptions=True,
        )
        answers = [r for r in results if not isinstance(r, BaseException)]
        if not answers:
            error = next(r for r in results if isinstance(r, BaseException))
            if not isinstance(error, RIPEStatLookupError):
                logger.warning("org_domains ripestat failed", error=str(error))
            sources.networks = "RIPEstat did not answer."
            return

        sources.answered += 1
        key = org_lookup.org_key(owner.name)
        kept: dict[int, SearchASN] = {}
        for answer in answers:
            for item in answer:
                holder = org_lookup.holder_name(item.holder)
                if org_lookup.org_key(holder) == key:
                    kept.setdefault(item.asn, item)
        ordered = sorted(kept.values(), key=lambda a: a.asn)
        sources.networks_found = ordered[:MAX_NETWORKS]
        count = len(ordered)
        sources.networks = (
            f"RIPEstat · {count} network{'s' if count != 1 else ''}"
            if count
            else "RIPEstat · no network registered to this name"
        )
        if count > MAX_NETWORKS:
            sources.caveats.append(f"Showing {MAX_NETWORKS} of {count} networks.")


def _hero(
    label: str,
    query: Query,
    owner: Owner | None,
    domains: int,
    new: int,
    tracked: int,
    sources: Sources,
):
    if query.kind == InputKind.DOMAIN and owner:
        read_from = (
            f"{owner.certificates} certificate{'s' if owner.certificates != 1 else ''} "
            "in this project"
            if owner.source == "certificates"
            else "WHOIS"
        )
        sub = f"Owner of {query.value}, read from {read_from}"
    elif query.kind == InputKind.EMAIL:
        sub = "Registrant email"
    else:
        sub = None
    networks = len(sources.networks_found)
    return hero(
        label,
        sub=sub,
        identity=glyph("building-2"),
        metric=metric(f"{domains:,}", "Domains"),
        marks=[
            mark(
                "New",
                tone=Tone.INFO.value if new else Tone.MUTED.value,
                note=f"{new:,}",
            ),
            mark(
                "Targets",
                tone=Tone.SUCCESS.value if tracked else Tone.MUTED.value,
                note=f"{tracked:,}",
            ),
            mark(
                "Networks",
                tone=Tone.INFO.value if networks else Tone.MUTED.value,
                note=f"{networks}",
            ),
        ],
    )


def _row(name: str, facts_: DomainFacts, found: estate.DomainEstate) -> list:
    evidence = ", ".join(
        EVIDENCE_LABELS[e]
        for e in (Evidence.CERTIFICATE.value, Evidence.REGISTRATION.value)
        if e in facts_.evidence
    )
    return [
        cell(name, mono=True, lookup=lookup(name, "whois")),
        cell(
            evidence,
            tone=Tone.SUCCESS.value if len(facts_.evidence) > 1 else Tone.NEUTRAL.value,
        ),
        cell(_iso(facts_.registered) or "", note=facts_.registrar or None),
        cell(_iso(facts_.last_certificate) or ""),
        _status(name, found),
    ]


def _status(name: str, found: estate.DomainEstate):
    if name in found.targets:
        return cell(
            "Target", tone=Tone.SUCCESS.value, href=f"/targets/{found.targets[name]}"
        )
    if name in found.seen:
        return cell("Seen in a scan", tone=Tone.INFO.value)
    return cell("New", tone=Tone.MUTED.value)


def _networks_block(networks: list[SearchASN]):
    return tags(
        [
            tag(
                f"AS{item.asn}",
                note=org_lookup.holder_name(item.holder) or None,
                identity=glyph("route"),
                lookup=lookup(f"AS{item.asn}", "whois"),
            )
            for item in networks
        ],
        title="Networks",
    )


def _similar_block(similar: list[CrtShOrganization]):
    return tags(
        [
            tag(
                organization.name,
                note=f"{organization.certs:,} certificate"
                f"{'s' if organization.certs != 1 else ''}",
                lookup=lookup(organization.name, OrgDomains.name),
            )
            for organization in similar
        ],
        title="Other organizations on matching certificates",
    )


def _summary(label: str, domains: int, new: int, networks: int) -> str:
    parts = [f"{domains:,} domain{'s' if domains != 1 else ''} for {label}"]
    if new:
        parts.append(f"{new:,} new")
    if networks:
        parts.append(f"{networks} network{'s' if networks != 1 else ''}")
    return " · ".join(parts)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None
