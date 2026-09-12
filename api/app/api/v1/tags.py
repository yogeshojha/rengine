from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.models.project import Project
from shared.models.tag import (
    PREDEFINED_TAGS,
    Tag,
    TagCreate,
    TagRead,
    TagUpdate,
)
from shared.utils.slug import add_with_unique_slug, unique_slug

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

    normalized_name = tag_in.name.lower()

    existing_tag = await session.execute(
        select(Tag).where(
            Tag.name == normalized_name,
            Tag.project_id == project.id,
        )
    )
    if existing_tag.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with this name exists in this project",
        )

    tag = Tag(
        name=normalized_name,
        color=tag_in.color,
        project_id=project.id,
        created_by=current_user.id,
    )
    try:
        await add_with_unique_slug(session, tag, normalized_name, project_id=project.id)
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with this name exists in this project",
        ) from e
    await session.refresh(tag)
    return tag


@router.post("/init-predefined", status_code=status.HTTP_201_CREATED)
async def init_predefined_tags(
    project_slug: Annotated[str, Query(description="Project slug")],
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
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
            slug = await unique_slug(
                session, Tag, tag_data["name"], project_id=project.id
            )
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
        tag.slug = await unique_slug(
            session, Tag, update_data["name"], project_id=project_id
        )

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
