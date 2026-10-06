"""The groups that concentrate a block's rows: 32 findings on 4 servers."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ask.estate.dimensions import groupable
from app.services.ask.estate.reading import fields_of, joined
from mcp.dimensions import Dimension
from shared.definitions.ask import (
    CAUSE_DETAIL_ROWS,
    CAUSE_DETAILS,
    CAUSE_KEYS,
    FALLBACK_CAUSE_SHARE,
    MAX_CAUSE_GROUPS,
    MAX_CAUSES,
    MIN_CAUSE_COVER,
    MIN_CAUSE_ROWS,
    CauseKey,
)
from shared.models.ask import BlockCause, BlockCauseDetail, BlockCauses
from shared.models.ip_address import IpAddress
from shared.models.vuln_template import VulnTemplate
from shared.services.asset_query import QuerySyntaxError
from shared.services.asset_query.parser import tokenize

CHECK = "template"


def spec(dimension: str, key: str | None) -> CauseKey | None:
    return next((c for c in CAUSE_KEYS.get(dimension, ()) if c.key == key), None)


async def _groups(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    scope: Any,
    query: str | None,
    key: str,
) -> Any | None:
    f = dim.build_filter(query, limit=1, offset=0)
    result = await dim.groups(session, scope, f, key, project_id)
    if getattr(result, "error", None) or not result.groups:
        return None
    return result


def _field(dim: Dimension, token: str | None) -> str | None:
    if not token:
        return None
    try:
        parsed = tokenize(token, dim.registry)
    except QuerySyntaxError:
        return None
    return next((t.field for t in parsed if t.kind == "CMP"), None)


async def _who(
    session: AsyncSession, project_id: uuid.UUID, values: list[str]
) -> dict[str, str]:
    if not values:
        return {}
    stmt = (
        select(IpAddress.ip, IpAddress.asn_org)
        .where(
            IpAddress.project_id == project_id,
            IpAddress.ip.in_(values),
            IpAddress.asn_org.isnot(None),
        )
        .distinct()
    )
    out: dict[str, str] = {}
    for ip, org in (await session.execute(stmt)).all():
        out.setdefault(ip, org)
    return out


async def _names(session: AsyncSession, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    stmt = select(VulnTemplate.template_id, VulnTemplate.name).where(
        VulnTemplate.template_id.in_(ids)
    )
    return {tid: name for tid, name in (await session.execute(stmt)).all() if name}


async def _finish(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    scope: Any,
    query: str | None,
    cause: CauseKey,
    result: Any,
) -> BlockCauses:
    top = result.groups[:MAX_CAUSES]
    who = (
        await _who(session, project_id, [str(g.value) for g in top])
        if cause.who
        else {}
    )
    picked: list[tuple[Any, str | None, list[Any]]] = []
    for index, group in enumerate(top):
        narrowed = joined(query, group.query) if group.query else None
        subs: list[Any] = []
        if cause.detail and narrowed and index < CAUSE_DETAIL_ROWS:
            try:
                sub = await _groups(
                    session, project_id, dim, scope, narrowed, cause.detail
                )
            except ValueError:
                sub = None
            subs = sub.groups[:CAUSE_DETAILS] if sub is not None else []
        picked.append((group, narrowed, subs))
    ids = {str(g.value) for g in top} if cause.key == CHECK else set()
    if cause.detail == CHECK:
        ids |= {str(d.value) for _, _, subs in picked for d in subs}
    names = await _names(session, ids)
    out: list[BlockCause] = []
    for group, narrowed, subs in picked:
        value = str(group.value)
        out.append(
            BlockCause(
                value=value,
                label=str(group.label or group.value),
                count=group.count,
                query=narrowed,
                who=who.get(value) or names.get(value),
                details=[
                    BlockCauseDetail(
                        label=str(d.label or d.value),
                        count=d.count,
                        hint=names.get(str(d.value)),
                    )
                    for d in subs
                ],
            )
        )
    return BlockCauses(
        key=cause.key,
        one=cause.one,
        many=cause.many,
        prep=cause.prep,
        mono=cause.mono,
        address=cause.who,
        total_groups=result.total_groups or len(result.groups),
        groups=out,
    )


async def pick(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    scope: Any,
    query: str | None,
    total: int | None,
    *,
    skip: frozenset[str] = frozenset(),
    named: set[str] | None = None,
) -> BlockCauses | None:
    """The first key that folds the rows into a few groups."""
    if not total or total < MIN_CAUSE_ROWS or not groupable(dim.key):
        return None
    named = fields_of(dim, query) if named is None else named
    fallback: tuple[CauseKey, Any] | None = None
    for cause in CAUSE_KEYS.get(dim.key, ()):
        if cause.key in named or cause.key in skip:
            continue
        result = await _groups(session, project_id, dim, scope, query, cause.key)
        if result is None or _field(dim, result.groups[0].query) in named:
            continue
        rows = result.rows or total
        groups = result.total_groups or len(result.groups)
        if (result.covered or 0) < rows * MIN_CAUSE_COVER or groups >= rows:
            continue
        if groups <= MAX_CAUSE_GROUPS:
            return await _finish(session, project_id, dim, scope, query, cause, result)
        if fallback is None and result.groups[0].count >= rows * FALLBACK_CAUSE_SHARE:
            fallback = (cause, result)
    if fallback is None:
        return None
    return await _finish(session, project_id, dim, scope, query, *fallback)


async def read(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    scope: Any,
    query: str | None,
    key: str,
) -> BlockCauses | None:
    cause = spec(dim.key, key)
    if cause is None or not groupable(dim.key):
        return None
    result = await _groups(session, project_id, dim, scope, query, key)
    if result is None:
        return None
    return await _finish(session, project_id, dim, scope, query, cause, result)
