"""Every project for an administrator, the member set for a standard user."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import delete, false, select, true
from sqlalchemy.dialects.postgresql import insert

from shared.models.project import Project
from shared.models.project_member import ProjectMember

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session
    from sqlalchemy.sql.elements import ColumnElement

    from shared.models.user import User

type ProjectSet = frozenset[uuid.UUID] | None

EVERY_PROJECT: ProjectSet = None


def _members_of(user_id: uuid.UUID):
    return select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)


async def member_projects(session: AsyncSession, user: User) -> ProjectSet:
    if user.is_superuser:
        return EVERY_PROJECT
    return frozenset((await session.scalars(_members_of(user.id))).all())


def member_projects_sync(session: Session, user: User) -> ProjectSet:
    if user.is_superuser:
        return EVERY_PROJECT
    return frozenset(session.scalars(_members_of(user.id)).all())


def may_open(access: ProjectSet, project_id: uuid.UUID | None) -> bool:
    if project_id is None:
        return False
    return access is None or project_id in access


def narrowed(access: ProjectSet, project_id: uuid.UUID | None) -> ProjectSet:
    """The named project alone, or the whole access when none is named."""
    if project_id is None:
        return access
    return frozenset({project_id}) if may_open(access, project_id) else frozenset()


def project_clause(access: ProjectSet, column) -> ColumnElement[bool]:
    if access is None:
        return true()
    if not access:
        return false()
    return column.in_(access)


def scoped(statement, access: ProjectSet, column):
    """The statement limited to rows whose project the access opens."""
    if access is None:
        return statement
    return statement.where(project_clause(access, column))


def opened_projects(access: ProjectSet):
    """Active projects the access opens, as a select of `Project`."""
    return scoped(select(Project).where(Project.is_active), access, Project.id)


async def project_ids(session: AsyncSession, access: ProjectSet) -> list[uuid.UUID]:
    """Ids of the active projects the access opens."""
    statement = scoped(
        select(Project.id).where(Project.is_active), access, Project.id
    ).order_by(Project.created_at)
    return list((await session.scalars(statement)).all())


def project_ids_sync(session: Session, access: ProjectSet) -> list[uuid.UUID]:
    statement = scoped(
        select(Project.id).where(Project.is_active), access, Project.id
    ).order_by(Project.created_at)
    return list(session.scalars(statement).all())


async def members_by_user(
    session: AsyncSession, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not user_ids:
        return {}
    rows = await session.execute(
        select(ProjectMember.user_id, ProjectMember.project_id)
        .where(ProjectMember.user_id.in_(user_ids))
        .order_by(ProjectMember.created_at)
    )
    found: dict[uuid.UUID, list[uuid.UUID]] = {}
    for user_id, project_id in rows.tuples():
        found.setdefault(user_id, []).append(project_id)
    return found


async def add_member(
    session: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    added_by: uuid.UUID | None,
) -> None:
    await session.execute(
        insert(ProjectMember)
        .values(project_id=project_id, user_id=user_id, added_by=added_by)
        .on_conflict_do_nothing(index_elements=["project_id", "user_id"])
    )


async def replace_members(
    session: AsyncSession,
    user_id: uuid.UUID,
    project_ids: list[uuid.UUID],
    added_by: uuid.UUID | None,
) -> bool:
    """Set the user's projects to these and report whether the set moved."""
    wanted = set(project_ids)
    held = set((await session.scalars(_members_of(user_id))).all())
    if wanted == held:
        return False
    if held - wanted:
        await session.execute(
            delete(ProjectMember).where(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id.in_(held - wanted),
            )
        )
    for project_id in sorted(wanted - held):
        await add_member(session, project_id, user_id, added_by)
    return True


def may_create_projects(user: User) -> bool:
    return user.is_superuser or user.can_create_projects
