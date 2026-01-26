from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.models.user import User, UserRead
from app.api.deps import CurrentSuperuser


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,  # Only superusers can list all users
    skip: int = 0,
    limit: int = 100,
):
    """
    List all users. **Admin only**.
    """

    # Get paginated users
    query = select(User).offset(skip).limit(limit)
    result = await session.execute(query)
    users = result.scalars().all()

    return users


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,  # superuser only
):
    """
    Get user by ID. **Admin only**.
    """
    from uuid import UUID

    try:
        uuid_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    result = await session.execute(select(User).where(User.id == uuid_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,  # superuser only
):
    """
    Delete user by ID. **Admin only**.
    """
    from uuid import UUID

    try:
        uuid_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Prevent self-deletion
    if uuid_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    result = await session.execute(select(User).where(User.id == uuid_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await session.delete(user)
    await session.commit()

    return {"message": f"User {user.username} deleted successfully"}
