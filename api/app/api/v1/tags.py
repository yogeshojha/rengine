import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.api.access import Access, OptionalProjectSlug, owned, project_by_slug
from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.target_labels import (
    refuse_if_in_use,
    rename,
    target_counts,
)
from shared.definitions.tripwires import ScopeKind
from shared.models.tag import Tag, TagCreate, TagRead, TagUpdate, TargetTag
from shared.services.project_access import scoped
from shared.utils.slug import add_with_unique_slug


def _read(tag: Tag, counts: dict[uuid.UUID, int]) -> TagRead:
    return TagRead.model_validate(tag).model_copy(
        update={"target_count": counts.get(tag.id, 0)}
    )


router = APIRouter(
    prefix="/tags",
    tags=["tags"],
)


@router.get("", response_model=list[TagRead])
async def list_tags(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    projects: OptionalProjectSlug,
):
    query = scoped(
        select(Tag).options(noload(Tag.targets)).order_by(Tag.name),
        projects,
        Tag.project_id,
    )
    tags = (await session.execute(query)).scalars().all()
    counts = await target_counts(session, TargetTag.tag_id, [t.id for t in tags])
    return [_read(t, counts) for t in tags]


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_in: TagCreate,
    current_user: CurrentUser,
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    project = await project_by_slug(session, access, tag_in.project_slug)
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
            detail="A tag with this name exists in this project.",
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
            detail="A tag with this name exists in this project.",
        ) from e
    await session.refresh(tag)
    return tag


@router.patch("/{tag_id}", response_model=TagRead)
async def update_tag(
    tag_id: uuid.UUID,
    tag_in: TagUpdate,
    _current_user: CurrentUser,
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    tag = await owned(session, access, Tag, tag_id, "Tag", noload(Tag.targets))
    if tag_in.name is not None:
        await rename(session, tag, tag_in.name, "Tag")
    if tag_in.color is not None:
        tag.color = tag_in.color
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with this name exists in this project.",
        ) from e
    counts = await target_counts(session, TargetTag.tag_id, [tag.id])
    return _read(tag, counts)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: uuid.UUID,
    _current_user: CurrentUser,
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    tag = await owned(session, access, Tag, tag_id, "Tag", noload(Tag.targets))
    await refuse_if_in_use(session, tag, ScopeKind.TAG)
    await session.delete(tag)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
