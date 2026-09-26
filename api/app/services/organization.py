"""Project organizations: one name per project, addressed by project slug and slug."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.services.project import project_id_for_slug, require_project_id
from shared.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
)
from shared.utils.slug import add_with_unique_slug, unique_slug

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

_ORGANIZATION_NOT_FOUND = "Organization not found"
_ORGANIZATION_EXISTS = "An organization with this name exists in this project"


def _normalized(name: str) -> str:
    return name.strip().lower()


class OrganizationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, project_slug: str | None = None) -> Sequence[Organization]:
        """Every organization, or one project's. A slug naming no project lists nothing."""
        query = select(Organization)
        if project_slug:
            project_id = await project_id_for_slug(self.session, project_slug)
            if project_id is None:
                return []
            query = query.where(Organization.project_id == project_id)
        return (await self.session.scalars(query)).all()

    async def create(self, data: OrganizationCreate, user_id: UUID) -> Organization:
        project_id = await require_project_id(self.session, data.project_slug)
        name = _normalized(data.name)
        if await self._named(name, project_id) is not None:
            raise _exists()
        organization = Organization(
            name=name,
            description=data.description,
            project_id=project_id,
            created_by=user_id,
        )
        try:
            await add_with_unique_slug(
                self.session, organization, name, project_id=project_id
            )
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise _exists() from e
        await self.session.refresh(organization)
        return organization

    async def get(self, project_slug: str, slug: str) -> Organization:
        project_id = await require_project_id(self.session, project_slug)
        return await self._own(slug, project_id)

    async def update(
        self, project_slug: str, slug: str, data: OrganizationUpdate
    ) -> Organization:
        project_id = await require_project_id(self.session, project_slug)
        organization = await self._own(slug, project_id)
        changes = data.model_dump(exclude_unset=True)

        if "name" in changes:
            name = _normalized(changes["name"])
            changes["name"] = name
            if await self._named(name, project_id, other_than=organization.id):
                raise _exists()
            organization.slug = await unique_slug(
                self.session, Organization, name, project_id=project_id
            )

        for field, value in changes.items():
            if field in Organization.model_fields:
                setattr(organization, field, value)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise _exists() from e
        await self.session.refresh(organization)
        return organization

    async def delete(self, project_slug: str, slug: str) -> None:
        project_id = await require_project_id(self.session, project_slug)
        organization = await self._own(slug, project_id)
        await self.session.delete(organization)
        await self.session.commit()

    async def _own(self, slug: str, project_id: UUID) -> Organization:
        organization = await self.session.scalar(
            select(Organization).where(
                Organization.slug == slug, Organization.project_id == project_id
            )
        )
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_ORGANIZATION_NOT_FOUND
            )
        return organization

    async def _named(
        self, name: str, project_id: UUID, *, other_than: UUID | None = None
    ) -> Organization | None:
        query = select(Organization).where(
            Organization.name == name, Organization.project_id == project_id
        )
        if other_than is not None:
            query = query.where(Organization.id != other_than)
        return await self.session.scalar(query)


def _exists() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=_ORGANIZATION_EXISTS
    )
