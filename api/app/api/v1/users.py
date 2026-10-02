from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.core.ratelimit import revoke_user_tokens
from app.core.security import hash_password
from app.utils.validation import validate_password_strength, validate_username
from shared.models.user import (
    User,
    UserAdminCreate,
    UserAdminUpdate,
    UserRead,
    UserSummary,
)

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
    skip: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    query = select(User).order_by(User.created_at).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserAdminCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,  # noqa: ARG001
):
    username = data.username.strip()
    email = data.email.strip().lower()
    try:
        validate_username(username)
        validate_password_strength(data.password, user_inputs=[email, username])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
        ) from e
    if "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Enter a valid email address.",
        )
    taken = await session.scalar(
        select(User).where((User.email == email) | (User.username == username))
    )
    if taken is not None:
        field = "email" if taken.email == email else "username"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this {field} exists.",
        )
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(data.password),
        is_superuser=data.is_superuser,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    data: UserAdminUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The signed-in account cannot change its own role or status.",
        )
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_superuser is not None:
        user.is_superuser = data.is_superuser
    await session.commit()
    if data.is_active is False:
        await revoke_user_tokens(user.id)
    await session.refresh(user)
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
            detail="Invalid user ID",
        ) from e

    if uuid_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The signed-in account cannot be deleted",
        )

    result = await session.execute(select(User).where(User.id == uuid_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    username = user.username
    await session.delete(user)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{username} created records on this instance. Disable the account instead.",
        ) from e

    return {"message": f"User {username} deleted"}
