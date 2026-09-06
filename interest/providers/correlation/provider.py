"""What stands out from the rest of the estate. A keyword list can never see this."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import bindparam, select, text

from interest.base import InterestProvider, RawSignal
from interest.context import InterestContext
from shared.definitions.interest import (
    EDGE_MAJORITY,
    MAX_EVIDENCE,
    MIN_ESTATE_FOR_RARITY,
    RARE_MAX_HOSTS,
    RARE_SHARE,
    InterestKind,
    InterestSource,
    kind_weight,
)
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services.asset_query import predicates as preds

logger = get_logger(__name__)

CAP = 300

_NETWORK_SQL = """
WITH resolved AS (
    SELECT id, name, asn, asn_org FROM subdomains
    WHERE scan_id = :sid AND is_excluded = false AND asn IS NOT NULL
),
total AS (SELECT count(*) AS t, count(DISTINCT asn) AS nets FROM resolved),
tally AS (SELECT asn, count(*) AS c FROM resolved GROUP BY asn)
SELECT r.id, r.name, r.asn, r.asn_org, t.c AS matches, tot.t AS estate
FROM resolved r
JOIN tally t ON t.asn = r.asn
CROSS JOIN total tot
WHERE tot.t >= :min_estate
  AND tot.nets > 1
  AND t.c <= GREATEST(1, floor(tot.t * :share))
ORDER BY t.c ASC, r.name
LIMIT :cap
"""

_TECH_SQL = """
WITH webhosts AS (
    SELECT id, name, tech FROM subdomains
    WHERE scan_id = :sid AND is_excluded = false AND http_status IS NOT NULL
      AND jsonb_typeof((tech)::jsonb) = 'array'
      AND jsonb_array_length((tech)::jsonb) > 0
),
total AS (SELECT count(*) AS t FROM webhosts),
exploded AS (
    SELECT w.id, w.name, e.value AS tech
    FROM webhosts w, jsonb_array_elements_text((w.tech)::jsonb) e
),
tally AS (SELECT tech, count(DISTINCT id) AS c FROM exploded GROUP BY tech)
SELECT DISTINCT ON (x.id) x.id, x.name, x.tech, t.c AS matches, tot.t AS estate
FROM exploded x
JOIN tally t ON t.tech = x.tech
CROSS JOIN total tot
WHERE tot.t >= :min_estate AND t.c <= :rare_max
ORDER BY x.id, t.c ASC, x.tech
LIMIT :cap
"""

_EDGE_SQL = """
WITH live AS (
    SELECT id, name, is_cdn FROM subdomains
    WHERE scan_id = :sid AND is_excluded = false AND http_status IS NOT NULL
),
agg AS (SELECT count(*) AS t, count(*) FILTER (WHERE is_cdn) AS c FROM live)
SELECT l.id, l.name, a.t AS estate, a.c AS behind
FROM live l CROSS JOIN agg a
WHERE a.t >= :min_estate AND a.c >= a.t * :majority AND l.is_cdn = false
ORDER BY l.name
LIMIT :cap
"""

_FAVICON_SQL = """
WITH shots AS (
    SELECT id, name, favicon_hash FROM subdomains
    WHERE scan_id = :sid AND is_excluded = false
      AND favicon_hash IS NOT NULL AND favicon_hash <> ''
),
total AS (SELECT count(*) AS t FROM shots),
tally AS (SELECT favicon_hash, count(*) AS c FROM shots GROUP BY favicon_hash)
SELECT s.id, s.name, s.favicon_hash, t.c AS matches, tot.t AS estate
FROM shots s
JOIN tally t ON t.favicon_hash = s.favicon_hash
CROSS JOIN total tot
WHERE tot.t >= :min_estate AND t.c <= :rare_max AND tot.t > t.c
ORDER BY t.c ASC, s.name
LIMIT :cap
"""


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


class CorrelationProvider(InterestProvider):
    name = "correlation"
    source = InterestSource.CORRELATION.value
    title = "Correlation"
    description = (
        "Hosts that stand out from the rest of the estate: a lone network, "
        "rare software, an asset outside the edge."
    )
    order = 20

    def available(self, ctx: InterestContext) -> bool:
        return ctx.host_total >= MIN_ESTATE_FOR_RARITY

    def evaluate(self, ctx: InterestContext) -> Iterable[RawSignal]:
        yield from self._guard(self._network, ctx)
        yield from self._guard(self._tech, ctx)
        yield from self._guard(self._edge, ctx)
        yield from self._guard(self._favicon, ctx)
        yield from self._guard(self._new, ctx)

    def _guard(self, fn, ctx: InterestContext) -> list[RawSignal]:
        try:
            return list(fn(ctx))
        except Exception:
            logger.warning("correlation signal failed", exc_info=True)
            return []

    def _rows(self, ctx: InterestContext, sql: str, **params):
        stmt = text(sql).bindparams(bindparam("sid", ctx.scan.id), **params)
        return ctx.session.execute(stmt).all()

    def _signal(self, row, kind: str, reason: str, evidence: str) -> RawSignal:
        return RawSignal(
            subdomain_id=row.id,
            host=row.name,
            source=InterestSource.CORRELATION.value,
            key=kind,
            kind=kind,
            weight=kind_weight(kind),
            label=self.title,
            reason=reason,
            evidence=evidence[:MAX_EVIDENCE],
        )

    def _network(self, ctx: InterestContext) -> Iterable[RawSignal]:
        rows = self._rows(
            ctx,
            _NETWORK_SQL,
            min_estate=MIN_ESTATE_FOR_RARITY,
            share=RARE_SHARE,
            cap=CAP,
        )
        for row in rows:
            org = row.asn_org or f"AS{row.asn}"
            reason = (
                f"On {org}, a network carrying {_plural(row.matches, 'host')} "
                f"of the {row.estate} that resolve here."
            )
            yield self._signal(
                row, InterestKind.NETWORK_OUTLIER.value, reason, f"asn:{row.asn}"
            )

    def _tech(self, ctx: InterestContext) -> Iterable[RawSignal]:
        rows = self._rows(
            ctx,
            _TECH_SQL,
            min_estate=MIN_ESTATE_FOR_RARITY,
            rare_max=RARE_MAX_HOSTS,
            cap=CAP,
        )
        for row in rows:
            reason = (
                f"Runs {row.tech}, found on {_plural(row.matches, 'host')} "
                f"of the {row.estate} that answered."
            )
            yield self._signal(
                row, InterestKind.RARE_TECHNOLOGY.value, reason, f"tech:{row.tech}"
            )

    def _edge(self, ctx: InterestContext) -> Iterable[RawSignal]:
        rows = self._rows(
            ctx,
            _EDGE_SQL,
            min_estate=MIN_ESTATE_FOR_RARITY,
            majority=EDGE_MAJORITY,
            cap=CAP,
        )
        for row in rows:
            share = round(100 * row.behind / row.estate) if row.estate else 0
            reason = (
                f"Answers directly while {share}% of the {row.estate} responding hosts "
                "here sit behind a CDN."
            )
            yield self._signal(
                row, InterestKind.UNPROTECTED_EDGE.value, reason, "not is:cdn"
            )

    def _favicon(self, ctx: InterestContext) -> Iterable[RawSignal]:
        rows = self._rows(
            ctx,
            _FAVICON_SQL,
            min_estate=MIN_ESTATE_FOR_RARITY,
            rare_max=RARE_MAX_HOSTS,
            cap=CAP,
        )
        for row in rows:
            reason = (
                f"Serves an icon shared by {_plural(row.matches, 'host')} of {row.estate}, "
                "distinct from the estate's standard application."
            )
            yield self._signal(
                row,
                InterestKind.RARE_IDENTITY.value,
                reason,
                f"favicon:{row.favicon_hash}",
            )

    def _new(self, ctx: InterestContext) -> Iterable[RawSignal]:
        stmt = (
            select(Subdomain.id, Subdomain.name)
            .where(
                Subdomain.scan_id == ctx.scan.id,
                Subdomain.is_excluded.is_(False),
                preds.is_new(),
            )
            .limit(CAP * 4)
        )
        for row in ctx.session.execute(stmt):
            yield RawSignal(
                subdomain_id=row.id,
                host=row.name,
                source=InterestSource.CORRELATION.value,
                key=InterestKind.NEWLY_APPEARED.value,
                kind=InterestKind.NEWLY_APPEARED.value,
                weight=kind_weight(InterestKind.NEWLY_APPEARED.value),
                label=self.title,
                reason="Absent from the previous scan of this target.",
                evidence="is:new",
                booster=True,
            )
