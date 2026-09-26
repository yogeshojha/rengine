from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.tag import TagService
from shared.models.tag import TagCreate, TagRead, TagUpdate

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TagService:
    return TagService(session)


@router.get("", response_model=list[TagRead])
async def list_tags(
    _current_user: CurrentUser,
    service: Annotated[TagService, Depends(get_service)],
    project_slug: Annotated[
        str | None, Query(description="Filter by project slug")
    ] = None,
):
    return await service.list(project_slug)


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_in: TagCreate,
    current_user: CurrentUser,
    service: Annotated[TagService, Depends(get_service)],
):
    return await service.create(tag_in, current_user.id)


@router.post("/init-predefined", status_code=status.HTTP_201_CREATED)
async def init_predefined_tags(
    project_slug: Annotated[str, Query(description="Project slug")],
    current_user: CurrentUser,
    service: Annotated[TagService, Depends(get_service)],
):
    created = await service.init_predefined(project_slug, current_user.id)
    return {"created": len(created), "tags": [tag.name for tag in created]}


@router.get("/{project_slug}/{slug}", response_model=TagRead)
async def get_tag(
    project_slug: str,
    slug: str,
    _current_user: CurrentUser,
    service: Annotated[TagService, Depends(get_service)],
):
    return await service.get(project_slug, slug)


@router.patch("/{project_slug}/{slug}", response_model=TagRead)
async def update_tag(
    project_slug: str,
    slug: str,
    tag_in: TagUpdate,
    _current_user: CurrentUser,
    service: Annotated[TagService, Depends(get_service)],
):
    return await service.update(project_slug, slug, tag_in)


@router.delete("/{project_slug}/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    project_slug: str,
    slug: str,
    _current_user: CurrentUser,
    service: Annotated[TagService, Depends(get_service)],
):
    await service.delete(project_slug, slug)
