from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.services.about import AboutRead, about

router = APIRouter(prefix="/about", tags=["About"])


@router.get("", response_model=AboutRead)
async def read_about(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AboutRead:
    """Version of the instance, its services and the tools it ships."""
    return await about(session)
