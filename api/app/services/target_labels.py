"""Rename and delete for the tags and organizations targets carry."""

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from shared.definitions.tripwires import ScopeKind
from shared.models.bounty_program import BountyProgram
from shared.models.organization import Organization
from shared.models.tripwire import Tripwire
from shared.models.watch import ProgramWatch
from shared.utils.slug import unique_slug


async def target_counts(
    session: AsyncSession, link_column: Any, ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    rows = await session.execute(
        select(link_column, func.count())
        .where(link_column.in_(ids))
        .group_by(link_column)
    )
    return dict(rows.tuples().all())


async def get_label[T](
    session: AsyncSession, model: type[T], label_id: uuid.UUID, noun: str
) -> T:
    options = [noload(model.targets)] if hasattr(model, "targets") else []
    row = await session.scalar(
        select(model).where(model.id == label_id).options(*options)
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{noun} not found"
        )
    return row


async def rename(session: AsyncSession, row: Any, name: str, noun: str) -> None:
    name = name.strip().lower()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{noun} name is empty."
        )
    if name == row.name:
        return
    model = type(row)
    taken = await session.scalar(
        select(model.id).where(
            model.name == name,
            model.project_id == row.project_id,
            model.id != row.id,
        )
    )
    if taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {noun.lower()} with this name exists in this project",
        )
    row.name = name
    row.slug = await unique_slug(session, model, name, project_id=row.project_id)


async def refuse_if_in_use(session: AsyncSession, row: Any, kind: ScopeKind) -> None:
    noun = "Tag" if kind == ScopeKind.TAG else "Organization"
    scoped = await session.execute(
        select(Tripwire.name, Tripwire.scope_ids).where(
            Tripwire.project_id == row.project_id, Tripwire.scope_kind == kind.value
        )
    )
    names = [
        name
        for name, ids in scoped.tuples().all()
        if str(row.id) in {str(i) for i in ids or []}
    ]
    if names:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{noun} {row.name} is the scope of tripwire {', '.join(names)}. "
                "Change the tripwire scope first."
            ),
        )
    if not isinstance(row, Organization):
        return
    program = await session.scalar(
        select(BountyProgram.name)
        .join(ProgramWatch, ProgramWatch.program_id == BountyProgram.id)
        .where(ProgramWatch.organization_id == row.id)
    )
    if program:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Organization {row.name} belongs to the watch on {program}. "
                "Delete the watch first."
            ),
        )
