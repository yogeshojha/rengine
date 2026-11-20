"""The caller's project access, resolved once per request."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, StreamUser, key_owner
from app.core.database import async_db_session, get_session
from shared.models.project import Project
from shared.models.user import User
from shared.services.project_access import (
    ProjectSet,
    may_open,
    member_projects,
    narrowed,
)

_STATE = "project_access"


def not_found(*, noun: str = "Project") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"{noun} not found."
    )


def check_open(
    access: ProjectSet, project_id: UUID | None, noun: str = "Project"
) -> UUID:
    """The project id when the access opens it, else the 404 an unknown id gets."""
    if not may_open(access, project_id):
        raise not_found(noun=noun)
    return project_id


def _remembered(request: Request, user: User) -> tuple[bool, ProjectSet]:
    held = getattr(request.state, _STATE, None)
    if held is not None and held[0] == user.id:
        return True, held[1]
    return False, None


async def get_access(
    request: Request,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectSet:
    known, access = _remembered(request, user)
    if not known:
        access = await member_projects(session, key_owner(request) or user)
        setattr(request.state, _STATE, (user.id, access))
    return access


async def get_stream_access(request: Request, user: StreamUser) -> ProjectSet:
    known, access = _remembered(request, user)
    if not known:
        async with async_db_session() as session:
            access = await member_projects(session, user)
        setattr(request.state, _STATE, (user.id, access))
    return access


Access = Annotated[ProjectSet, Depends(get_access)]
StreamAccess = Annotated[ProjectSet, Depends(get_stream_access)]


async def project_id_param(
    access: Access,
    project_id: Annotated[UUID, Query(description="Project ID")],
) -> UUID:
    return check_open(access, project_id)


async def optional_project_param(
    access: Access,
    project_id: Annotated[UUID | None, Query(description="Project ID")] = None,
) -> ProjectSet:
    if project_id is not None:
        check_open(access, project_id)
    return narrowed(access, project_id)


async def _slug_project(session: AsyncSession, access: ProjectSet, slug: str) -> UUID:
    project_id = await session.scalar(select(Project.id).where(Project.slug == slug))
    return check_open(access, project_id)


async def project_slug_param(
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_slug: Annotated[str, Query(description="Project slug", max_length=100)],
) -> UUID:
    return await _slug_project(session, access, project_slug)


async def optional_project_slug_param(
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_slug: Annotated[
        str | None, Query(description="Project slug", max_length=100)
    ] = None,
) -> ProjectSet:
    if project_slug is None:
        return access
    return frozenset({await _slug_project(session, access, project_slug)})


ProjectId = Annotated[UUID, Depends(project_id_param)]
OptionalProject = Annotated[ProjectSet, Depends(optional_project_param)]
ProjectSlug = Annotated[UUID, Depends(project_slug_param)]
OptionalProjectSlug = Annotated[ProjectSet, Depends(optional_project_slug_param)]


async def project_by_slug(
    session: AsyncSession, access: ProjectSet, slug: str
) -> Project:
    """The project a body names by slug, when the access opens it."""
    project = await session.scalar(select(Project).where(Project.slug == slug))
    check_open(access, project.id if project else None)
    return project


async def owned[T](
    session: AsyncSession,
    access: ProjectSet,
    model: type[T],
    row_id: Any,
    noun: str,
    *options: Any,
) -> T:
    """The row by id when its project is open to the access, else the 404 an unknown id gets."""
    row = await session.scalar(
        select(model).where(model.id == row_id).options(*options)
    )
    if row is None or not may_open(access, row.project_id):
        raise not_found(noun=noun)
    return row


async def project_of(session: AsyncSession, model: Any, row_id: Any) -> UUID | None:
    return await session.scalar(select(model.project_id).where(model.id == row_id))


async def require_owned(
    session: AsyncSession, access: ProjectSet, model: Any, row_id: Any, noun: str
) -> UUID:
    """The row's project id when the access opens it, read without loading the row."""
    return check_open(access, await project_of(session, model, row_id), noun)
