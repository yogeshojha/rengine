from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.sql.selectable import Exists

from shared.definitions.asset_query import COUNT_CAP, QueryExample
from shared.logging import get_logger
from shared.models.asset_query import QueryCounts, QueryLead, QueryLeads

from .ast import QuerySyntaxError

logger = get_logger(__name__)

_TOTAL_IDX = 0
_CORRELATED = (Exists, TextClause)


def _branch(query, index: int):
    """Count up to the cap."""
    matches = query.cte(f"branch_{index}").prefix_with("MATERIALIZED")
    capped = select(matches.c[0]).limit(COUNT_CAP + 1).subquery()
    return select(func.count()).select_from(capped).scalar_subquery().label(f"n{index}")


def _row_local(predicate) -> bool:
    """Whether the predicate reads only its own row."""
    return not any(isinstance(el, _CORRELATED) for el in visitors.iterate(predicate))


def _single_pass(base, local: list[tuple[int, object | None]], branches: list):
    columns = [func.count().label(f"n{_TOTAL_IDX}")]
    for index, predicate in local:
        count = func.count() if predicate is None else func.count().filter(predicate)
        columns.append(count.label(f"n{index}"))
    return base.with_only_columns(
        *columns, *branches, maintain_column_froms=True
    ).order_by(None)


async def _counts(
    session: AsyncSession, base, local, branches, *, total: bool
) -> dict[int, int]:
    """Every count in one statement."""
    if not local and not total:
        if not branches:
            return {}
        statement = select(*branches)
    else:
        statement = _single_pass(base, local, branches)
    row = (await session.execute(statement)).one()
    return {int(key[1:]): int(value) for key, value in row._mapping.items()}


def _rank(lead: QueryLead, total: int) -> int:
    if lead.count == 0:
        return 2
    return 1 if total and lead.count >= total else 0


async def count_named(
    session: AsyncSession, base, predicates: Mapping[str, object | None]
) -> QueryCounts:
    """Exact counts for each named predicate over one scope, in one statement."""
    keys = list(predicates)
    local: list[tuple[int, object | None]] = []
    branches = []
    for index, key in enumerate(keys, start=1):
        predicate = predicates[key]
        if predicate is None or _row_local(predicate):
            local.append((index, predicate))
        else:
            branches.append(_branch(base.where(predicate), index))
    counts = await _counts(session, base, local, branches, total=False)
    return QueryCounts(
        counts={k: min(counts.get(i, 0), COUNT_CAP) for i, k in enumerate(keys, 1)},
        capped={k: counts.get(i, 0) > COUNT_CAP for i, k in enumerate(keys, 1)},
        computed=True,
    )


async def count_queries(
    session: AsyncSession,
    base,
    queries: Sequence[str],
    predicate_for: Callable[[str], object | None],
) -> QueryCounts:
    """Exact counts for the queries over one scope."""
    predicates: dict[str, object | None] = {}
    for query in queries:
        try:
            predicates[query] = predicate_for(query)
        except QuerySyntaxError as exc:
            logger.warning(
                "search count does not compile", query=query, error=exc.message
            )
    return await count_named(session, base, predicates)


async def build_leads(
    session: AsyncSession,
    base,
    examples: Sequence[QueryExample],
    predicate_for: Callable[[str], object | None],
    *,
    filtered: bool = False,
    known: Mapping[str, int] | None = None,
) -> QueryLeads:
    kept = []
    local: list[tuple[int, object | None]] = []
    branches = []
    stored: dict[int, int] = {}
    for example in examples:
        if known and example.query in known:
            kept.append(example)
            stored[len(kept)] = known[example.query]
            continue
        try:
            predicate = predicate_for(example.query)
        except QuerySyntaxError as exc:
            logger.warning(
                "search example does not compile",
                query=example.query,
                error=exc.message,
            )
            continue
        index = len(kept) + 1
        kept.append(example)
        if predicate is None or _row_local(predicate):
            local.append((index, predicate))
        else:
            branches.append(_branch(base.where(predicate), index))

    counts = await _counts(session, base, local, branches, total=True)
    counts.update(stored)
    total = counts.get(_TOTAL_IDX, 0)
    leads = [
        QueryLead(
            query=example.query,
            description=example.description,
            group=example.group,
            generic=example.generic,
            count=min(counts.get(index + 1, 0), COUNT_CAP),
            capped=counts.get(index + 1, 0) > COUNT_CAP,
        )
        for index, example in enumerate(kept)
    ]
    leads.sort(key=lambda lead: _rank(lead, total))
    return QueryLeads(
        leads=leads,
        total=min(total, COUNT_CAP),
        total_capped=total > COUNT_CAP,
        filtered=filtered,
        computed=True,
    )
