"""Saved queries and keyword lists. The matching engine is the asset query grammar itself."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select

from interest.base import InterestProvider, RawSignal
from interest.context import InterestContext
from shared.definitions.interest import (
    MAX_EVIDENCE,
    MAX_REASON,
    InterestSource,
    RuleMode,
    kind_label,
    kind_weight,
)
from shared.logging import get_logger
from shared.models.interest import InterestRule
from shared.models.subdomain import Subdomain
from shared.services.asset_query import QueryContext, compile_query, parse_query
from shared.services.asset_query.ast import QuerySyntaxError

logger = get_logger(__name__)

MAX_HOSTS_PER_RULE = 500


def rule_query(rule: InterestRule) -> str:
    """A keyword list is a query the user never has to see."""
    if rule.mode != RuleMode.KEYWORD.value:
        return rule.query.strip()
    words = [w.strip() for w in (rule.keywords or []) if str(w).strip()]
    if not words:
        return ""
    fields = [f for f in (rule.keyword_fields or []) if f in ("host", "title")] or [
        "host"
    ]
    listed = ",".join(_escape(w) for w in words)
    parts = [f"{field}:[{listed}]" for field in fields]
    query = parts[0] if len(parts) == 1 else "(" + " or ".join(parts) + ")"
    return f"{query} and is:live" if rule.live_only else query


def _escape(word: str) -> str:
    cleaned = word.replace('"', "").replace(",", "").replace("]", "").strip()
    return f'"{cleaned}"' if " " in cleaned else cleaned


class RulesProvider(InterestProvider):
    name = "rules"
    source = InterestSource.RULE.value
    title = "Rules"
    description = "Keyword lists and saved queries, evaluated against the scan."
    order = 10

    def evaluate(self, ctx: InterestContext) -> Iterable[RawSignal]:
        query_ctx = QueryContext(scan_id=ctx.scan.id, now=ctx.now)
        for rule in ctx.rules:
            if not rule.enabled:
                continue
            yield from self._one(ctx, rule, query_ctx)

    def _one(
        self, ctx: InterestContext, rule: InterestRule, query_ctx: QueryContext
    ) -> Iterable[RawSignal]:
        text_query = rule_query(rule)
        if not text_query:
            return
        try:
            predicate = compile_query(parse_query(text_query), query_ctx)
        except QuerySyntaxError as exc:
            logger.warning(
                "interest rule did not compile", rule=rule.name, error=exc.message
            )
            return
        if predicate is None:
            return

        stmt = (
            select(Subdomain.id, Subdomain.name)
            .where(
                Subdomain.scan_id == ctx.scan.id,
                Subdomain.is_excluded.is_(False),
                predicate,
            )
            .limit(MAX_HOSTS_PER_RULE)
        )
        source = (
            InterestSource.KEYWORD.value
            if rule.mode == RuleMode.KEYWORD.value
            else InterestSource.RULE.value
        )
        weight = rule.weight if rule.weight is not None else kind_weight(rule.kind)
        reason = (rule.description or kind_label(rule.kind))[:MAX_REASON]
        for row in ctx.session.execute(stmt):
            yield RawSignal(
                subdomain_id=row.id,
                host=row.name,
                source=source,
                key=str(rule.id),
                kind=rule.kind,
                weight=weight,
                label=rule.name,
                reason=reason,
                evidence=text_query[:MAX_EVIDENCE],
                rule_id=rule.id,
            )
