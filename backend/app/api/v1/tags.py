from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.models.project import Project
from app.models.tags import (
    PREDEFINED_TAGS,
    Tag,
    TagCreate,
    TagRead,
    TagUpdate,
)
from app.utils.slug import generate_slug

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
)


@router.get("", response_model=list[TagRead])
async def list_tags(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    project_slug: Annotated[
        str | None, Query(description="Filter by project slug")
    ] = None,
):
    query = select(Tag)

    if project_slug:
        project_result = await session.execute(
            select(Project.id).where(Project.slug == project_slug)
        )
        project_id = project_result.scalar_one_or_none()
        if project_id:
            query = query.where(Tag.project_id == project_id)
        else:
            return []

    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_in: TagCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(
        select(Project).where(Project.slug == tag_in.project_slug)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    existing_tag = await session.execute(
        select(Tag).where(
            Tag.name == tag_in.name,
            Tag.project_id == project.id,
        )
    )
    if existing_tag.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag with this name already exists in this project",
        )

    slug = generate_slug(tag_in.name)

    tag = Tag(
        name=tag_in.name,
        slug=slug,
        color=tag_in.color,
        project_id=project.id,
        created_by=current_user.id,
    )
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


@router.post("/init-predefined", status_code=status.HTTP_201_CREATED)
async def init_predefined_tags(
    project_slug: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Initialize predefined tags for a project"""
    project_result = await session.execute(
        select(Project).where(Project.slug == project_slug)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    created_tags = []
    for tag_data in PREDEFINED_TAGS:
        existing_tag = await session.execute(
            select(Tag).where(
                Tag.name == tag_data["name"],
                Tag.project_id == project.id,
            )
        )
        if not existing_tag.scalar_one_or_none():
            slug = generate_slug(tag_data["name"])
            tag = Tag(
                name=tag_data["name"],
                slug=slug,
                color=tag_data["color"],
                project_id=project.id,
                created_by=current_user.id,
            )
            session.add(tag)
            created_tags.append(tag)

    await session.commit()
    return {"created": len(created_tags), "tags": [tag.name for tag in created_tags]}


@router.get("/{project_slug}/{slug}", response_model=TagRead)
async def get_tag(
    project_slug: str,
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(
        select(Project.id).where(Project.slug == project_slug)
    )
    project_id = project_result.scalar_one_or_none()

    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    result = await session.execute(
        select(Tag).where(
            Tag.slug == slug,
            Tag.project_id == project_id,
        )
    )
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    return tag


@router.patch("/{project_slug}/{slug}", response_model=TagRead)
async def update_tag(
    project_slug: str,
    slug: str,
    tag_in: TagUpdate,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(
        select(Project.id).where(Project.slug == project_slug)
    )
    project_id = project_result.scalar_one_or_none()

    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    result = await session.execute(
        select(Tag).where(
            Tag.slug == slug,
            Tag.project_id == project_id,
        )
    )
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    update_data = tag_in.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_slug = generate_slug(update_data["name"])
        tag.slug = new_slug

    for field, value in update_data.items():
        setattr(tag, field, value)

    await session.commit()
    await session.refresh(tag)
    return tag


@router.delete("/{project_slug}/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    project_slug: str,
    slug: str,
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project_result = await session.execute(
        select(Project.id).where(Project.slug == project_slug)
    )
    project_id = project_result.scalar_one_or_none()

    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    result = await session.execute(
        select(Tag).where(
            Tag.slug == slug,
            Tag.project_id == project_id,
        )
    )
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    await session.delete(tag)
    await session.commit()
