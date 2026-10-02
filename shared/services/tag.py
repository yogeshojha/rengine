import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Tag
from shared.models.tag import MAX_TAG_LEN
from shared.utils.slug import add_with_unique_slug
from shared.utils.validation import clean_name


async def get_or_create_tag(
    name: str,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> Tag:
    normalized_name = clean_name(name, max_len=MAX_TAG_LEN).lower()

    result = await session.execute(
        select(Tag).where(
            Tag.name == normalized_name,
            Tag.project_id == project_id,
        )
    )
    tag = result.scalar_one_or_none()

    if not tag:
        tag = Tag(
            name=normalized_name,
            project_id=project_id,
            created_by=user_id,
        )
        await add_with_unique_slug(session, tag, normalized_name, project_id=project_id)

    return tag
