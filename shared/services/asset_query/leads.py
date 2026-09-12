from __future__ import annotations

from collections.abc import Callable, Sequence

from sqlalchemy import func, literal_column, select, union_all
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
_CHUNK = 16
_CORRELATED = (Exists, TextClause)


def _branch(query, index: int):
    return select(
        literal_column(str(index)).label("idx"), func.count().label("n")
    ).select_from(query.limit(COUNT_CAP + 1).subquery())


def _row_local(predicate) -> bool:
    """Whether the predicate reads only its own row."""
    return not any(isinstance(el, _CORRELATED) for el in visitors.iterate(predicate))


def _single_pass(base, local: list[tuple[int, object | None]]):
    columns = [func.count().label(f"n{_TOTAL_IDX}")]
    for index, predicate in local:
        count = func.count() if predicate is None else func.count().filter(predicate)
        columns.append(count.label(f"n{index}"))
    return base.with_only_columns(*columns, maintain_column_froms=True).order_by(None)


def _rank(lead: QueryLead, total: int) -> int:
    if lead.count == 0:
        return 2
    return 1 if total and lead.count >= total else 0


async def count_queries(
    session: AsyncSession,
    base,
    queries: Sequence[str],
    predicate_for: Callable[[str], object | None],
) -> QueryCounts:
    """Exact counts for the queries over one scope."""
    kept: list[str] = []
    local: list[tuple[int, object | None]] = []
    branches = []
    for query in queries:
        predicate = predicate_for(query)
        index = len(kept) + 1
        kept.append(query)
        if predicate is None or _row_local(predicate):
            local.append((index, predicate))
        else:
            branches.append(_branch(base.where(predicate), index))
    counts: dict[int, int] = {}
    if local:
        row = (await session.execute(_single_pass(base, local))).one()
        counts.update({int(key[1:]): int(value) for key, value in row._mapping.items()})
    for start in range(0, len(branches), _CHUNK):
        chunk = branches[start : start + _CHUNK]
        rows = await session.execute(chunk[0] if len(chunk) == 1 else union_all(*chunk))
        counts.update({int(idx): int(n) for idx, n in rows.all()})
    return QueryCounts(
        counts={q: min(counts.get(i + 1, 0), COUNT_CAP) for i, q in enumerate(kept)},
        capped={q: counts.get(i + 1, 0) > COUNT_CAP for i, q in enumerate(kept)},
        computed=True,
    )


async def build_leads(
    session: AsyncSession,
    base,
    examples: Sequence[QueryExample],
    predicate_for: Callable[[str], object | None],
    *,
    filtered: bool = False,
) -> QueryLeads:
    kept = []
    local: list[tuple[int, object | None]] = []
    branches = []
    for example in examples:
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

    counts: dict[int, int] = {}
    row = (await session.execute(_single_pass(base, local))).one()
    counts.update({int(key[1:]): int(value) for key, value in row._mapping.items()})
    for start in range(0, len(branches), _CHUNK):
        chunk = branches[start : start + _CHUNK]
        rows = await session.execute(chunk[0] if len(chunk) == 1 else union_all(*chunk))
        counts.update({int(idx): int(n) for idx, n in rows.all()})
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
