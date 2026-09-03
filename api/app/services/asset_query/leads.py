from __future__ import annotations

from sqlalchemy import func, literal_column, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.asset_query import COUNT_CAP, EXAMPLES
from shared.logging import get_logger
from shared.models.asset_query import QueryLead, QueryLeads

from .ast import QuerySyntaxError
from .compiler import QueryContext, compile_query
from .parser import parse_query

logger = get_logger(__name__)

_TOTAL_IDX = 0


def _branch(query, index: int):
    return select(
        literal_column(str(index)).label("idx"), func.count().label("n")
    ).select_from(query.limit(COUNT_CAP + 1).subquery())


def _rank(lead: QueryLead, total: int) -> int:
    if lead.count == 0:
        return 2
    return 1 if total and lead.count >= total else 0


async def build_leads(
    session: AsyncSession, base, ctx: QueryContext, *, filtered: bool = False
) -> QueryLeads:
    kept = []
    branches = [_branch(base, _TOTAL_IDX)]
    for example in EXAMPLES:
        try:
            predicate = compile_query(parse_query(example.query), ctx)
        except QuerySyntaxError as exc:
            logger.warning(
                "search example does not compile",
                query=example.query,
                error=exc.message,
            )
            continue
        scoped = base.where(predicate) if predicate is not None else base
        branches.append(_branch(scoped, len(kept) + 1))
        kept.append(example)

    rows = await session.execute(union_all(*branches))
    counts = {int(idx): int(n) for idx, n in rows.all()}
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
