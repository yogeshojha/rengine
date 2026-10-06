"""The targets an estate thread asks about."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.target_scope import TargetFilter, resolve_targets
from shared.definitions.ask import FOLD_CHARS, MAX_SCOPE_VALUES
from shared.models.ask import EstateScope, EstateScopeRead
from shared.models.organization import Organization
from shared.models.scan import Scan
from shared.models.tag import Tag
from shared.models.target import Target
from shared.services.asset_query.tokens import token

ALL_TARGETS = "All targets"
SCAN_GONE = "Scan deleted"
SCAN_TIMES = (Scan.completed_at, Scan.started_at, Scan.created_at)


@dataclass(frozen=True)
class Resolved:
    targets: frozenset[uuid.UUID]
    filtered: bool
    label: str
    values: tuple[str, ...]
    # one run read alone
    scan: uuid.UUID | None = None
    scan_at: datetime | None = None
    # the target clause every count and link carries
    clause: str | None = None

    @property
    def count(self) -> int:
        return len(self.targets)

    @property
    def links(self) -> list[str]:
        """Every target value a scoped link names, none when unscoped or too many."""
        if not self.filtered or (self.scan is None and self.clause is None):
            return []
        return list(self.values)

    @property
    def shown(self) -> tuple[str, ...]:
        return self.values[:MAX_SCOPE_VALUES]


def stored(scope: EstateScope) -> dict:
    return scope.model_dump(mode="json")


def parsed(raw: dict | None) -> EstateScope:
    try:
        return EstateScope.model_validate(raw or {})
    except ValueError:
        return EstateScope()


def _filter(scope: EstateScope) -> TargetFilter:
    return TargetFilter(tuple(scope.target_ids), scope.organization_id, scope.tag_id)


async def _label(session: AsyncSession, scope: EstateScope, values: list[str]) -> str:
    if scope.tag_id:
        tag = await session.get(Tag, scope.tag_id)
        if tag is not None:
            return f"Tag {tag.name}"
    if scope.organization_id:
        org = await session.get(Organization, scope.organization_id)
        if org is not None:
            return org.name
    if len(values) == 1:
        return values[0]
    return f"{len(values)} targets"


async def _scan(
    session: AsyncSession, project_id: uuid.UUID, scan_id: uuid.UUID
) -> Resolved | None:
    row = (
        await session.execute(
            select(Scan.id, Scan.target_id, Target.target_value, *SCAN_TIMES)
            .join(Target, Target.id == Scan.target_id)
            .where(Scan.id == scan_id, Scan.project_id == project_id)
        )
    ).first()
    if row is None:
        return None
    at = row.completed_at or row.started_at or row.created_at
    label = f"{row.target_value} · scan of {at:%Y-%m-%d %H:%M} UTC"
    return Resolved(
        frozenset({row.target_id}), True, label, (row.target_value,), row.id, at
    )


async def resolve(
    session: AsyncSession, project_id: uuid.UUID, raw: dict | None
) -> Resolved:
    scope = parsed(raw)
    if scope.scan_id is not None:
        found = await _scan(session, project_id, scope.scan_id)
        return found or Resolved(frozenset(), True, SCAN_GONE, (), scope.scan_id)
    spec = _filter(scope)
    picked = await resolve_targets(session, project_id, spec)
    query = select(Target.id, Target.target_value).where(
        Target.project_id == project_id
    )
    if picked is not None:
        query = query.where(Target.id.in_(picked))
    rows = (await session.execute(query.order_by(Target.target_value))).all()
    values = [row.target_value for row in rows]
    targets = frozenset(row.id for row in rows)
    if picked is None:
        return Resolved(targets, False, ALL_TARGETS, tuple(values))
    label = await _label(session, scope, values)
    clause = target_clause(values)
    return Resolved(
        targets,
        True,
        label,
        tuple(values),
        clause=clause if clause and len(clause) <= FOLD_CHARS else None,
    )


def target_clause(values: list[str]) -> str | None:
    """The clause a scoped link puts before its query."""
    quoted = [token("target", "=", v)[len("target=") :] for v in values]
    if not quoted:
        return None
    return f"target={quoted[0]}" if len(quoted) == 1 else f"target=[{','.join(quoted)}]"


async def foreign(
    session: AsyncSession, project_id: uuid.UUID, scope: EstateScope
) -> str | None:
    """Why a scope names something outside the project, or None."""
    if scope.scan_id is not None:
        held = await session.scalar(
            select(func.count())
            .select_from(Scan)
            .where(Scan.project_id == project_id, Scan.id == scope.scan_id)
        )
        if not held:
            return "The scan in the scope is not in this project."
    if scope.target_ids:
        held = await session.scalar(
            select(func.count())
            .select_from(Target)
            .where(Target.project_id == project_id, Target.id.in_(scope.target_ids))
        )
        if (held or 0) != len(set(scope.target_ids)):
            return "A target in the scope is not in this project."
    for model, row_id, noun in (
        (Organization, scope.organization_id, "organization"),
        (Tag, scope.tag_id, "tag"),
    ):
        if row_id is None:
            continue
        row = await session.get(model, row_id)
        if row is None or row.project_id != project_id:
            return f"The {noun} in the scope is not in this project."
    return None


def read(raw: dict | None, resolved: Resolved) -> EstateScopeRead:
    scope = parsed(raw)
    return EstateScopeRead(
        target_ids=scope.target_ids,
        organization_id=scope.organization_id,
        tag_id=scope.tag_id,
        scan_id=resolved.scan,
        scan_at=resolved.scan_at,
        scan_target=resolved.values[0] if resolved.scan_at else None,
        label=resolved.label,
        targets=resolved.count,
        filtered=resolved.filtered,
        links=resolved.links,
    )
