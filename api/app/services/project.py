"""Projects: named by slug in every URL, resolved here once."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import func, select

from app.services.scan_engine import ScanEngineService
from shared.models.organization import Organization
from shared.models.project import Project, ProjectCreate, ProjectSummary
from shared.models.tag import Tag
from shared.models.target import Target
from shared.utils.slug import add_with_unique_slug

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_NOT_FOUND = "Project not found"


def project_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND
    )


async def project_id_for_slug(session: AsyncSession, slug: str) -> UUID | None:
    """The id of the project this slug names, or None."""
    return await session.scalar(select(Project.id).where(Project.slug == slug))


async def require_project_id(session: AsyncSession, slug: str) -> UUID:
    """The id of the project this slug names, or a 404."""
    project_id = await project_id_for_slug(session, slug)
    if project_id is None:
        raise project_not_found()
    return project_id


async def require_project(
    session: AsyncSession, slug: str, *, active_only: bool = False
) -> Project:
    """The project this slug names, or a 404. A soft-deleted one counts unless `active_only`."""
    query = select(Project).where(Project.slug == slug)
    if active_only:
        query = query.where(Project.is_active)
    project = await session.scalar(query)
    if project is None:
        raise project_not_found()
    return project


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, *, include_inactive: bool = False) -> Sequence[Project]:
        query = select(Project)
        if not include_inactive:
            query = query.where(Project.is_active)
        return (await self.session.scalars(query)).all()

    async def get(self, slug: str) -> Project:
        return await require_project(self.session, slug, active_only=True)

    async def summary(self, slug: str) -> ProjectSummary:
        project = await require_project(self.session, slug, active_only=True)
        return ProjectSummary(
            project=project,
            stats={
                "targets": await self._count(Target.id, Target.project_id, project),
                "organizations": await self._count(
                    Organization.id, Organization.project_id, project
                ),
                "tags": await self._count(Tag.id, Tag.project_id, project),
            },
        )

    async def create(self, data: ProjectCreate, user_id: UUID) -> Project:
        project = Project(
            name=data.name,
            description=data.description,
            label=data.label,
            created_by=user_id,
        )
        await add_with_unique_slug(self.session, project, data.name)
        await ScanEngineService(self.session).ensure_builtin(project.id, user_id)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def deactivate(self, slug: str) -> None:
        """Soft delete: the project leaves every list but its rows stay."""
        project = await require_project(self.session, slug)
        project.is_active = False
        await self.session.commit()

    async def _count(self, column, owner, project: Project) -> int:
        return await self.session.scalar(
            select(func.count(column)).where(owner == project.id)
        )
