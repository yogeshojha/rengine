"""Enrich candidate domains with passive intelligence: resolution, ports, registration."""

from __future__ import annotations

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.definitions.domains import takeover_provider
from shared.definitions.estate import MAX_DOSSIER_PORTS, MAX_ENRICH_PER_TICK
from shared.http import egress_proxy
from shared.logging import get_logger
from shared.models.target import Target
from shared.services import estate_dossier
from shared.services.asset_query.lead_cache import bump_sync
from shared.utils.datetime import utc_now
from tools.dnsx.service import DnsxService, DnsxServiceError
from tools.naabu.client import NaabuClient, NaabuError, NaabuOptions
from tools.whois.parser import parse_domain_response
from tools.whois.providers.whoisit import RDAPProvider, RDAPProviderError

logger = get_logger(__name__)


def _resolve(
    dns: DnsxService, domain: str
) -> tuple[bool | None, list[str], list[str], str | None]:
    try:
        r = dns.do_recon(domain)
    except DnsxServiceError:
        return None, [], [], None
    cname = r.cname[0] if r.cname else None
    return bool(r.a or r.aaaa), list(r.a), list(r.aaaa), cname


def _ports(ips: list[str]) -> list[int]:
    if not ips:
        return []
    try:
        records = NaabuClient(options=NaabuOptions()).passive(ips)
    except NaabuError:
        return []
    return sorted({r["port"] for r in records})[:MAX_DOSSIER_PORTS]


def _registration(rdap: RDAPProvider, domain: str):
    try:
        parsed = parse_domain_response(rdap.lookup_domain(domain), domain)
    except (RDAPProviderError, ValueError, TypeError):
        return None, None
    registrar = next((e.name for e in parsed.entities.registrar if e.name), None)
    return parsed.registration_date, registrar


@shared_task(name="app.tasks.estate.enrich", max_retries=0)
def enrich(limit: int = MAX_ENRICH_PER_TICK) -> dict:
    dns = DnsxService(timeout=20, retry=1, query_timeout=3)
    rdap = RDAPProvider(proxy_url=egress_proxy())
    done = 0
    projects: set = set()
    with get_sync_session() as session:
        rows = estate_dossier.pending(session, limit=limit)
        for row in rows:
            resolves, a, aaaa, cname = _resolve(dns, row.domain)
            registered_at, registrar = _registration(rdap, row.domain)
            row.resolves = resolves
            row.a = a
            row.aaaa = aaaa
            row.cname = cname
            row.ports = _ports(a + aaaa)
            row.registered_at = registered_at
            row.registrar = registrar
            row.takeover_provider = (
                takeover_provider(cname) if cname and not (a or aaaa) else None
            )
            row.checked_at = utc_now()
            row.updated_at = utc_now()
            projects.add(row.project_id)
            done += 1
        session.commit()
        targets = (
            session.execute(
                select(Target.id).where(Target.project_id.in_(projects))
            ).scalars()
            if projects
            else []
        )
        target_ids = list(targets)
    if target_ids:
        bump_sync(target_ids)
    if done:
        logger.info("estate dossier enriched", domains=done)
    return {"enriched": done, "more": len(rows) >= limit}
