import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Organization
from shared.models.organization import MAX_ORG_LEN
from shared.utils.slug import add_with_unique_slug
from shared.utils.validation import clean_name


async def get_or_create_organization(
    name: str,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
    description: str | None = None,
) -> Organization:
    normalized_name = clean_name(name, max_len=MAX_ORG_LEN).lower()

    organization = await _by_name(session, normalized_name, project_id)

    if not organization:
        organization = Organization(
            name=normalized_name,
            description=description,
            project_id=project_id,
            created_by=user_id,
        )
        try:
            await add_with_unique_slug(
                session, organization, normalized_name, project_id=project_id
            )
        except IntegrityError:
            organization = await _by_name(session, normalized_name, project_id)
            if organization is None:
                raise

    return organization


async def _by_name(
    session: AsyncSession, name: str, project_id: uuid.UUID
) -> Organization | None:
    result = await session.execute(
        select(Organization).where(
            Organization.name == name, Organization.project_id == project_id
        )
    )
    return result.scalar_one_or_none()
