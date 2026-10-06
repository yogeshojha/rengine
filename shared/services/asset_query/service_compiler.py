from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import cast, func, literal, or_
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import array as pg_array

from shared.definitions.ai_services import CATEGORY_LABELS as AI_CATEGORIES
from shared.definitions.asset_query import SERVICE_FLAGS, SERVICE_QUERY, Op
from shared.definitions.ports import PortSource
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability

from . import predicates as preds
from .ast import Compare
from .scope import QueryScope
from .terms import (
    address_match,
    cdn_match,
    date_match,
    folded_match,
    int_coerce,
    json_array_match,
    negate,
    number_match,
    string_match,
    target_match,
    tri_state,
)
from .values import PRIVATE_NETWORKS, asn_number
from .walk import flags, walker

_IPV4 = 4
_IPV6 = 6


@dataclass(frozen=True)
class ServiceQueryContext:
    scope: QueryScope
    now: datetime
    source: Any


def _within(ctx: ServiceQueryContext, cidr: str):
    return ctx.source.c.inet.op("<<=")(cast(literal(cidr), INET))


def _ai(cmp: Compare, ctx: ServiceQueryContext):
    services = ctx.source.c.ai_services
    state = tri_state(cmp)
    if state is not None:
        present = func.jsonb_array_length(services) > 0
        matched = present if state else ~present
        return negate(matched) if cmp.op is Op.NE else matched
    if cmp.op in (Op.RE, Op.NRE):
        return json_array_match(services, cmp)
    values = [v.lower() for v in cmp.values]
    categories = [v for v in values if v in AI_CATEGORIES]
    keys = [v for v in values if v not in AI_CATEGORIES]
    parts = []
    if keys:
        parts.append(func.jsonb_exists_any(services, pg_array(keys)))
    if categories:
        parts.append(
            func.jsonb_exists_any(ctx.source.c.ai_categories, pg_array(categories))
        )
    matched = or_(*parts)
    return negate(matched) if cmp.op is Op.NE else matched


def _ai_model(cmp: Compare, ctx: ServiceQueryContext):
    models = ctx.source.c.ai_models
    state = tri_state(cmp)
    if state is None:
        return json_array_match(models, cmp)
    present = func.jsonb_array_length(models) > 0
    matched = present if state else ~present
    return negate(matched) if cmp.op is Op.NE else matched


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.service_is_new(ctx.source, ctx.scope),
    "http": lambda ctx: ctx.source.c.is_http.is_(True),
    "tls": lambda ctx: ctx.source.c.tls.is_(True),
    "sensitive": lambda ctx: ctx.source.c.sensitive.is_(True),
    "named": lambda ctx: ctx.source.c.product.isnot(None),
    "passive": lambda ctx: ctx.source.c.source == PortSource.INTERNETDB.value,
    "confirmed": lambda ctx: ctx.source.c.source != PortSource.INTERNETDB.value,
    "cdn": lambda ctx: ctx.source.c.is_cdn.is_(True),
    "hosted": lambda ctx: ctx.source.c.host_count > 0,
    "private": lambda ctx: or_(*[_within(ctx, n) for n in PRIVATE_NETWORKS]),
    "v4": lambda ctx: ctx.source.c.version == _IPV4,
    "v6": lambda ctx: ctx.source.c.version == _IPV6,
    "vulnerable": lambda ctx: preds.service_vuln(
        ctx.scope, ctx.source.c.ip, ctx.source.c.port
    ),
    "kev": lambda ctx: preds.service_vuln(
        ctx.scope, ctx.source.c.ip, ctx.source.c.port, Vulnerability.is_kev.is_(True)
    ),
}

_SERVICE_BUILDERS = {
    "target": lambda c, ctx: target_match(ctx.source.c.target_id, c),
    "port": lambda c, ctx: number_match(ctx.source.c.port, c, int_coerce(c)),
    "seen": lambda c, ctx: date_match(
        ctx.source.c.discovered_at, c, ctx.now, future=False
    ),
    "service": lambda c, ctx: string_match(ctx.source.c.service_name, c),
    "class": lambda c, ctx: string_match(ctx.source.c.service_class, c),
    "protocol": lambda c, ctx: string_match(ctx.source.c.protocol, c),
    "source": lambda c, ctx: string_match(ctx.source.c.source, c),
    "product": lambda c, ctx: string_match(ctx.source.c.product, c),
    "version": lambda c, ctx: string_match(ctx.source.c.version_text, c),
    "banner": lambda c, ctx: string_match(ctx.source.c.banner, c),
    "ip": lambda c, ctx: address_match(ctx.source.c.ip, ctx.source.c.inet, c),
    "asn": lambda c, ctx: number_match(
        ctx.source.c.asn, c, lambda raw: asn_number(raw, c.start, c.end)
    ),
    "org": lambda c, ctx: string_match(ctx.source.c.asn_org, c),
    "country": lambda c, ctx: string_match(ctx.source.c.country, c),
    "cdn": lambda c, ctx: cdn_match(ctx.source.c.cdn_name, ctx.source.c.is_cdn, c),
    "host": lambda c, ctx: preds.resolved_by(
        ctx.scope, ctx.source.c.ip, folded_match(Subdomain.name, c)
    ),
    "status": lambda c, ctx: number_match(ctx.source.c.status_code, c, int_coerce(c)),
    "vuln": lambda c, ctx: preds.service_vuln(
        ctx.scope,
        ctx.source.c.ip,
        ctx.source.c.port,
        string_match(Vulnerability.severity, c),
    ),
    "cve": lambda c, ctx: preds.service_vuln(
        ctx.scope,
        ctx.source.c.ip,
        ctx.source.c.port,
        json_array_match(Vulnerability.cve_ids, c),
    ),
    "ai": _ai,
    "ai.model": _ai_model,
    "is": flags(_FLAG_BUILDERS, SERVICE_FLAGS),
}


compile_service_query = walker(SERVICE_QUERY, _SERVICE_BUILDERS)
