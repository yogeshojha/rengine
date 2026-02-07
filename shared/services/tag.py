import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Tag
from shared.utils.slug import generate_slug


async def get_or_create_tag(
    name: str,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
    color: str = "#6B7280",
) -> Tag:
    normalized_name = name.lower()

    result = await session.execute(
        select(Tag).where(
            Tag.name == normalized_name,
            Tag.project_id == project_id,
        )
    )
    tag = result.scalar_one_or_none()

    if not tag:
        slug = generate_slug(normalized_name)
        tag = Tag(
            name=normalized_name,
            slug=slug,
            color=color,
            project_id=project_id,
            created_by=user_id,
        )
        session.add(tag)

    return tag
