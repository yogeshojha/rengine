"""How the estate spells a value: technologies, networks, targets, tags."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ask.estate.blocks import BlockError, dimension_of, groups
from app.services.ask.estate.dimensions import groupable
from app.services.ask.estate.scope import Resolved, target_clause
from shared.definitions.ask import FOLD_CHARS, MAX_LOOKUP_VALUES, BlockKind, TargetKey
from shared.models.ask import AnswerBlock
from shared.models.organization import Organization
from shared.models.tag import Tag, TargetTag
from shared.models.target import Target, TargetOrganization

MAX_MEMBERS = 30
LOOKUP_GROUPS = 1_000


async def _members(
    session: AsyncSession,
    project_id: uuid.UUID,
    link,
    column,
    row_id: uuid.UUID,
    resolved: Resolved,
) -> list[str]:
    stmt = (
        select(Target.target_value)
        .join(link, link.target_id == Target.id)
        .where(
            Target.project_id == project_id,
            column == row_id,
            Target.id.in_(resolved.targets),
        )
        .order_by(Target.target_value)
    )
    return list((await session.execute(stmt)).scalars().all())


async def _targets(
    session: AsyncSession, project_id: uuid.UUID, text: str, resolved: Resolved
) -> list[dict]:
    stmt = (
        select(Target.target_value)
        .where(
            Target.project_id == project_id,
            Target.id.in_(resolved.targets),
            func.lower(Target.target_value).contains(text.lower()),
        )
        .order_by(Target.target_value)
        .limit(MAX_LOOKUP_VALUES)
    )
    return [
        {"value": v, "query": target_clause([v])}
        for v in (await session.execute(stmt)).scalars().all()
    ]


async def _labels(
    session: AsyncSession,
    project_id: uuid.UUID,
    text: str,
    key: str,
    resolved: Resolved,
) -> list[dict]:
    if key == TargetKey.TAG.value:
        model, link, column = Tag, TargetTag, TargetTag.tag_id
    else:
        model, link, column = (
            Organization,
            TargetOrganization,
            TargetOrganization.organization_id,
        )
    stmt = (
        select(model.id, model.name)
        .where(
            model.project_id == project_id,
            func.lower(model.name).contains(text.lower()),
        )
        .order_by(model.name)
        .limit(MAX_LOOKUP_VALUES)
    )
    out = []
    for row in (await session.execute(stmt)).all():
        members = await _members(session, project_id, link, column, row.id, resolved)
        clause = target_clause(members)
        out.append(
            {
                "value": row.name,
                "targets": members[:MAX_MEMBERS],
                "target_count": len(members),
                "query": clause if clause and len(clause) <= FOLD_CHARS else None,
            }
        )
    return out


async def lookup(
    session: AsyncSession,
    project_id: uuid.UUID,
    resolved: Resolved,
    *,
    key: str,
    text: str,
    dimension: str | None = None,
) -> dict:
    """Values of a group key, a target, a tag or an organization that contain text."""
    needle = " ".join((text or "").split())
    if not needle:
        msg = "Pass the text to look up."
        raise BlockError(msg)
    if key == TargetKey.TARGET.value:
        return {
            "key": key,
            "matches": await _targets(session, project_id, needle, resolved),
        }
    if key in (TargetKey.TAG.value, TargetKey.ORGANIZATION.value):
        return {
            "key": key,
            "matches": await _labels(session, project_id, needle, key, resolved),
        }
    dim = dimension_of(dimension)
    if not groupable(dim.key):
        msg = f"{dim.label} values cannot be looked up. Use a field in a query."
        raise BlockError(msg)
    block = AnswerBlock(
        id="lookup", kind=BlockKind.GROUPS.value, dimension=dim.key, group_by=key
    )
    data = await groups(session, project_id, resolved, block, cap=LOOKUP_GROUPS)
    low = needle.casefold()
    matches = [
        {"value": g.value, "label": g.label, "count": g.count, "query": g.query}
        for g in data.groups
        if low in g.label.casefold() or low in g.value.casefold()
    ][:MAX_LOOKUP_VALUES]
    return {"key": key, "dimension": dim.key, "matches": matches}
