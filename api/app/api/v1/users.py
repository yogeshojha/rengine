from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from shared.models.user import User, UserRead, UserSummary

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/summary", response_model=UserSummary)
async def get_user_summary(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _current_user: CurrentUser,
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("", response_model=list[UserRead])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,  # noqa: ARG001
    skip: int = 0,
    limit: int = 100,
):
    query = select(User).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,  # noqa: ARG001
):
    try:
        uuid_id = UUID(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        ) from e

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
    current_user: CurrentSuperuser,
):
    try:
        uuid_id = UUID(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        ) from e

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
