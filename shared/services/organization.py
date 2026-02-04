import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Organization
from app.utils.slug import generate_slug


async def get_or_create_organization(
    name: str,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
    description: str | None = None,
) -> Organization:
    normalized_name = name.lower()

    result = await session.execute(
        select(Organization).where(
            Organization.name == normalized_name,
            Organization.project_id == project_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        slug = generate_slug(normalized_name)
        organization = Organization(
            name=normalized_name,
            slug=slug,
            description=description,
            project_id=project_id,
            created_by=user_id,
        )
        session.add(organization)

    return organization
