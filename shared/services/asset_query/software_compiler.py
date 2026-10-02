from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, cast, func, or_
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.asset_query import SOFTWARE_FLAGS, SOFTWARE_QUERY, Op
from shared.definitions.evidence import Evidence
from shared.definitions.software import Caveat, Confidence, VersionSource
from shared.definitions.threat_intel import BANDS_BY_KEY
from shared.models.software import SoftwareCve

from . import predicates as preds
from .ast import Compare
from .scope import QueryScope
from .terms import (
    address_match,
    date_match,
    float_coerce,
    int_coerce,
    negate,
    number_match,
    string_match,
    target_match,
)
from .walk import flags, walker


@dataclass(frozen=True)
class SoftwareQueryContext:
    scope: QueryScope
    now: datetime


LIKELY_EPSS = BANDS_BY_KEY["likely"].floor


def _caveat(cmp: Compare, _ctx: SoftwareQueryContext):
    branches = [
        func.jsonb_exists(cast(SoftwareCve.caveats, JSONB), raw.lower())
        for raw in cmp.values
    ]
    matched = or_(*branches)
    return negate(matched) if cmp.op is Op.NE else matched


def _overdue(ctx: SoftwareQueryContext):
    return and_(
        SoftwareCve.kev_due_date.isnot(None),
        SoftwareCve.kev_due_date < ctx.now.date(),
    )


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.software_is_new(ctx.scope),
    "kev": lambda _ctx: SoftwareCve.is_kev.is_(True),
    "ransomware": lambda _ctx: SoftwareCve.kev_ransomware.is_(True),
    "overdue": _overdue,
    "likely": lambda _ctx: SoftwareCve.epss_score >= LIKELY_EPSS,
    "firm": lambda _ctx: SoftwareCve.confidence == Confidence.HIGH.value,
    "conditional": lambda _ctx: func.jsonb_exists(
        cast(SoftwareCve.caveats, JSONB), Caveat.CONDITIONAL.value
    ),
    "backport": lambda _ctx: func.jsonb_exists(
        cast(SoftwareCve.caveats, JSONB), Caveat.BACKPORT.value
    ),
    "fingerprinted": lambda _ctx: (
        SoftwareCve.version_source == VersionSource.FINGERPRINT.value
    ),
    "stated": lambda _ctx: SoftwareCve.version_source == VersionSource.BANNER.value,
    "web": lambda _ctx: SoftwareCve.http_asset_id.isnot(None),
    "service": lambda _ctx: SoftwareCve.port_id.isnot(None),
    "corroborated": lambda _ctx: SoftwareCve.evidence == Evidence.CORROBORATED.value,
    "fixable": lambda _ctx: SoftwareCve.fixed_in.is_not(None),
}


_BUILDERS = {
    "target": lambda c, _ctx: target_match(SoftwareCve.target_id, c),
    "cve": lambda c, _ctx: string_match(SoftwareCve.cve, c),
    "software": lambda c, _ctx: string_match(SoftwareCve.name, c),
    "product": lambda c, _ctx: string_match(SoftwareCve.product, c),
    "vendor": lambda c, _ctx: string_match(SoftwareCve.vendor, c),
    "version": lambda c, _ctx: string_match(SoftwareCve.version, c),
    "source": lambda c, _ctx: string_match(SoftwareCve.version_source, c),
    "severity": lambda c, _ctx: string_match(SoftwareCve.severity, c),
    "cvss": lambda c, _ctx: number_match(SoftwareCve.cvss_score, c, float_coerce(c)),
    "epss": lambda c, _ctx: number_match(SoftwareCve.epss_score, c, float_coerce(c)),
    "rank": lambda c, _ctx: number_match(SoftwareCve.exploit_score, c, int_coerce(c)),
    "confidence": lambda c, _ctx: string_match(SoftwareCve.confidence, c),
    "evidence": lambda c, _ctx: string_match(SoftwareCve.evidence, c),
    "caveat": _caveat,
    "host": lambda c, _ctx: string_match(SoftwareCve.host, c),
    "ip": lambda c, _ctx: address_match(
        SoftwareCve.ip, preds.inet_of(SoftwareCve.ip), c
    ),
    "port": lambda c, _ctx: number_match(SoftwareCve.port, c, int_coerce(c)),
    "seen": lambda c, ctx: date_match(
        SoftwareCve.discovered_at, c, ctx.now, future=False
    ),
    "is": flags(_FLAG_BUILDERS, SOFTWARE_FLAGS),
}


compile_software_query = walker(SOFTWARE_QUERY, _BUILDERS)
