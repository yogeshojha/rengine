"""Counted facts about a block's rows, and the rows in scope."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ask.estate.reading import fields_of, joined
from mcp.dimensions import Dimension
from shared.definitions.ask import BLOCK_FACTS, MAX_BLOCK_QUERY, MAX_FACTS
from shared.logging import get_logger
from shared.models.ask import BlockFactRead

logger = get_logger(__name__)

Counted = tuple[int, bool]


async def count(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    scope: Any,
    query: str | None,
) -> Counted | None:
    f = dim.build_filter(query, limit=1, offset=0)
    page = await dim.search(session, scope, f, project_id)
    if getattr(page, "error", None):
        return None
    return int(page.total or 0), bool(page.total_capped)


async def count_many(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    scope: Any,
    queries: list[str],
) -> dict[str, Counted]:
    """One statement where the dimension counts in batch, a search per query elsewhere."""
    batch = getattr(dim.service(session), "counts", None)
    if batch is not None:
        found = await (
            batch(project_id, scope, queries)
            if dim.needs_project
            else batch(scope, queries)
        )
        if found.computed:
            return {
                q: (found.counts[q], bool(found.capped.get(q)))
                for q in queries
                if q in found.counts
            }
    out: dict[str, Counted] = {}
    for query in queries:
        try:
            got = await count(session, project_id, dim, scope, query)
        except ValueError as exc:
            logger.info("ask fact not counted", query=query, error=str(exc))
            continue
        if got is not None:
            out[query] = got
    return out


async def read(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    scope: Any,
    query: str | None,
    total: int | None,
    capped: bool,
) -> list[BlockFactRead]:
    """Facts that hold for some of the rows and not all."""
    if not total:
        return []
    named = fields_of(dim, query)
    wanted = [
        (fact, joined(query, fact.token))
        for fact in BLOCK_FACTS.get(dim.key, ())
        if not fields_of(dim, fact.token) & named
    ]
    wanted = [(f, q) for f, q in wanted if len(q) <= MAX_BLOCK_QUERY]
    counted = await count_many(session, project_id, dim, scope, [q for _, q in wanted])
    out: list[BlockFactRead] = []
    for fact, narrowed in wanted:
        if narrowed not in counted:
            continue
        n, cut = counted[narrowed]
        if not n or (n >= total and not capped):
            continue
        out.append(
            BlockFactRead(
                title=fact.title,
                question=fact.question,
                query=narrowed,
                count=n,
                capped=cut,
            )
        )
        if len(out) >= MAX_FACTS:
            break
    return out
