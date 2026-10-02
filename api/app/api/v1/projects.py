from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services.scan_engine import ScanEngineService
from shared.models.project import Project, ProjectCreate, ProjectRead
from shared.utils.slug import add_with_unique_slug

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Project).where(Project.is_active))
    return result.scalars().all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project = Project(
        name=project_in.name,
        description=project_in.description,
        label=project_in.label,
        created_by=current_user.id,
    )
    await add_with_unique_slug(session, project, project_in.name)
    await ScanEngineService(session).ensure_builtin(project.id, current_user.id)
    await session.commit()
    await session.refresh(project)
    return project
