import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Organization
from shared.utils.slug import add_with_unique_slug
from shared.utils.validation import clean_name


async def get_or_create_organization(
    name: str,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
    description: str | None = None,
) -> Organization:
    normalized_name = clean_name(name, max_len=100).lower()

    result = await session.execute(
        select(Organization).where(
            Organization.name == normalized_name,
            Organization.project_id == project_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        organization = Organization(
            name=normalized_name,
            description=description,
            project_id=project_id,
            created_by=user_id,
        )
        await add_with_unique_slug(
            session, organization, normalized_name, project_id=project_id
        )

    return organization
