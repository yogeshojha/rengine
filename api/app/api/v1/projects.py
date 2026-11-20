from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import Access
from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.scan_engine import ScanEngineService
from shared.logging import get_logger
from shared.models.project import Project, ProjectCreate, ProjectRead
from shared.services.project_access import (
    add_member,
    may_create_projects,
    opened_projects,
)
from shared.utils.slug import add_with_unique_slug

logger = get_logger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    _current_user: CurrentUser,
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(opened_projects(access).order_by(Project.created_at))
    return result.scalars().all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    if not may_create_projects(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account cannot create projects.",
        )
    project = Project(
        name=project_in.name,
        description=project_in.description,
        label=project_in.label,
        created_by=current_user.id,
    )
    await add_with_unique_slug(
        session, project, project_in.name, opaque=not current_user.is_superuser
    )
    await add_member(session, project.id, current_user.id, current_user.id)
    await ScanEngineService(session).ensure_builtin(project.id, current_user.id)
    await session.commit()
    await session.refresh(project)
    logger.info("project created", project=str(project.id), by=str(current_user.id))
    return project
