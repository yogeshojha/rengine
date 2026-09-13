"""Vulnerability statement building, shared by the api's search and the worker's export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import case, cast, func, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.asset_query import VULN_QUERY
from shared.definitions.vulnerabilities import ACTIONABLE_SEVERITIES, SEVERITY_ORDER
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import (
    QueryScope,
    VulnQueryContext,
    compile_vuln_query,
    parse_query,
    vuln_corroborated,
    vuln_corroborated_ids,
    vuln_is_new,
    vuln_state,
    vuln_suppressed,
)

if TYPE_CHECKING:
    from datetime import datetime

    from shared.models.vulnerability import VulnerabilityFilter


def severity_rank():
    return case(
        {name: index for index, name in enumerate(SEVERITY_ORDER)},
        value=Vulnerability.severity,
        else_=len(SEVERITY_ORDER),
    )


def context(scope: QueryScope, now: datetime) -> VulnQueryContext:
    return VulnQueryContext(scope=scope, now=now)


def apply_filter(query, f: VulnerabilityFilter, scope: QueryScope):
    if f.severities:
        query = query.where(Vulnerability.severity.in_(f.severities))
    elif not f.include_info:
        query = query.where(Vulnerability.severity.in_(ACTIONABLE_SEVERITIES))
    if f.protocols:
        query = query.where(Vulnerability.protocol.in_(f.protocols))
    if f.templates:
        query = query.where(Vulnerability.template_id.in_(f.templates))
    if f.hosts:
        query = query.where(Vulnerability.host.in_(f.hosts))
    if f.scanners:
        query = query.where(Vulnerability.scanner.in_(f.scanners))
    if f.tags:
        query = query.where(
            or_(
                *[
                    func.jsonb_exists(cast(Vulnerability.tags, JSONB), tag)
                    for tag in f.tags
                ]
            )
        )
    if f.kev:
        query = query.where(Vulnerability.is_kev.is_(True))
    if f.cve:
        query = query.where(
            func.jsonb_array_length(cast(Vulnerability.cve_ids, JSONB)) > 0
        )
    if f.new:
        query = query.where(vuln_is_new(scope))
    if f.corroborated:
        query = query.where(vuln_corroborated(scope))
    if f.states:
        query = query.where(vuln_state(scope).in_(f.states))
    elif not f.include_suppressed:
        query = query.where(not_(vuln_suppressed(scope)))
    return query


def order(query, f: VulnerabilityFilter, scope: QueryScope):
    if f.sort == "risk":
        confirmed = vuln_corroborated_ids(scope).subquery()
        return query.outerjoin(confirmed, confirmed.c.id == Vulnerability.id).order_by(
            severity_rank().asc(),
            Vulnerability.is_kev.desc(),
            Vulnerability.exploit_score.desc(),
            confirmed.c.id.isnot(None).desc(),
            Vulnerability.epss_score.desc().nulls_last(),
            Vulnerability.cvss_score.desc().nulls_last(),
            Vulnerability.template_id.asc(),
            Vulnerability.matched_at.asc(),
        )
    column = {
        "severity": severity_rank(),
        "name": Vulnerability.template_name,
        "template": Vulnerability.template_id,
        "host": Vulnerability.host,
        "seen": Vulnerability.discovered_at,
        "cvss": Vulnerability.cvss_score,
        "epss": Vulnerability.epss_score,
        "exploit": Vulnerability.exploit_score,
        "type": Vulnerability.protocol,
    }.get(f.sort, severity_rank())
    primary = column.desc() if f.order == "desc" else column.asc()
    return query.order_by(
        primary.nulls_last(),
        Vulnerability.template_id.asc(),
        Vulnerability.matched_at.asc(),
    )


def scoped(scope: QueryScope, f: VulnerabilityFilter, columns=None):
    base = select(Vulnerability) if columns is None else select(*columns)
    base = base.where(scope.match(Vulnerability.scan_id))
    return apply_filter(base, f, scope)


def compiled(scope: QueryScope, f: VulnerabilityFilter, now: datetime):
    return compile_vuln_query(parse_query(f.q, VULN_QUERY), context(scope, now))
