"""Project tags: named once per project, addressed by project slug and tag slug."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.services.project import project_id_for_slug, require_project_id
from shared.models.tag import PREDEFINED_TAGS, Tag, TagCreate, TagUpdate
from shared.utils.slug import add_with_unique_slug, unique_slug

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

_TAG_NOT_FOUND = "Tag not found"
_TAG_EXISTS = "A tag with this name exists in this project"


class TagService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, project_slug: str | None = None) -> Sequence[Tag]:
        """Every tag, or one project's. A slug naming no project lists nothing."""
        query = select(Tag)
        if project_slug:
            project_id = await project_id_for_slug(self.session, project_slug)
            if project_id is None:
                return []
            query = query.where(Tag.project_id == project_id)
        return (await self.session.scalars(query)).all()

    async def create(self, data: TagCreate, user_id: UUID) -> Tag:
        project_id = await require_project_id(self.session, data.project_slug)
        name = data.name.lower()
        if await self._named(name, project_id) is not None:
            raise _exists()
        tag = Tag(
            name=name,
            color=data.color,
            project_id=project_id,
            created_by=user_id,
        )
        try:
            await add_with_unique_slug(self.session, tag, name, project_id=project_id)
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise _exists() from e
        await self.session.refresh(tag)
        return tag

    async def init_predefined(self, project_slug: str, user_id: UUID) -> list[Tag]:
        """Add the predefined tags this project does not have yet."""
        project_id = await require_project_id(self.session, project_slug)
        created: list[Tag] = []
        for spec in PREDEFINED_TAGS:
            if await self._named(spec["name"], project_id) is not None:
                continue
            tag = Tag(
                name=spec["name"],
                slug=await unique_slug(
                    self.session, Tag, spec["name"], project_id=project_id
                ),
                color=spec["color"],
                project_id=project_id,
                created_by=user_id,
            )
            self.session.add(tag)
            created.append(tag)
        await self.session.commit()
        return created

    async def get(self, project_slug: str, slug: str) -> Tag:
        project_id = await require_project_id(self.session, project_slug)
        return await self._own(slug, project_id)

    async def update(self, project_slug: str, slug: str, data: TagUpdate) -> Tag:
        project_id = await require_project_id(self.session, project_slug)
        tag = await self._own(slug, project_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes:
            tag.slug = await unique_slug(
                self.session, Tag, changes["name"], project_id=project_id
            )
        for field, value in changes.items():
            setattr(tag, field, value)
        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def delete(self, project_slug: str, slug: str) -> None:
        project_id = await require_project_id(self.session, project_slug)
        tag = await self._own(slug, project_id)
        await self.session.delete(tag)
        await self.session.commit()

    async def _own(self, slug: str, project_id: UUID) -> Tag:
        tag = await self.session.scalar(
            select(Tag).where(Tag.slug == slug, Tag.project_id == project_id)
        )
        if tag is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_TAG_NOT_FOUND
            )
        return tag

    async def _named(self, name: str, project_id: UUID) -> Tag | None:
        return await self.session.scalar(
            select(Tag).where(Tag.name == name, Tag.project_id == project_id)
        )


def _exists() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_TAG_EXISTS)
