from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.core.ratelimit import revoke_user_tokens
from app.core.security import hash_password_async
from app.core.validation_errors import validation_detail
from app.services.access_keys import revoke_account_keys
from app.utils.validation import validate_password_strength, validate_username
from shared.logging import get_logger
from shared.models.project import Project
from shared.models.scan_engine import ScanEngine
from shared.models.user import (
    User,
    UserAdminCreate,
    UserAdminUpdate,
    UserProjects,
    UserRead,
    UserSummary,
)
from shared.services.project_access import members_by_user, replace_members

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


async def read_users(session: AsyncSession, users: list[User]) -> list[UserRead]:
    held = await members_by_user(session, [u.id for u in users])
    return [
        UserRead.model_validate(u).model_copy(
            update={"project_ids": held.get(u.id, [])}
        )
        for u in users
    ]


async def _known_projects(session: AsyncSession, project_ids: list[UUID]) -> list[UUID]:
    wanted = list(dict.fromkeys(project_ids))
    found = set(
        (await session.scalars(select(Project.id).where(Project.id.in_(wanted)))).all()
    )
    missing = [p for p in wanted if p not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_detail(
                ["body", "project_ids"], f"Project {missing[0]} not found."
            ),
        )
    return wanted


async def _other_user(session: AsyncSession, user_id: UUID, current_user: User) -> User:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The signed-in account cannot change its own role or status.",
        )
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return user


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
            detail="User not found.",
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
    return await read_users(session, list(result.scalars().all()))


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserAdminCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,
):
    username = data.username.strip()
    email = data.email.strip().lower()
    try:
        validate_username(username)
        validate_password_strength(data.password, user_inputs=[email, username])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_detail(["body"], str(e)),
        ) from e
    if "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_detail(["body", "email"], "Enter a valid email address."),
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
    project_ids = await _known_projects(session, data.project_ids)
    user = User(
        email=email,
        username=username,
        hashed_password=await hash_password_async(data.password),
        is_superuser=data.is_superuser,
        can_create_projects=data.can_create_projects,
    )
    session.add(user)
    await session.flush()
    await replace_members(session, user.id, project_ids, current_user.id)
    await session.commit()
    await session.refresh(user)
    logger.info(
        "user created",
        user=str(user.id),
        superuser=user.is_superuser,
        can_create_projects=user.can_create_projects,
        projects=len(project_ids),
        by=str(current_user.id),
    )
    return (await read_users(session, [user]))[0]


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    data: UserAdminUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,
):
    user = await _other_user(session, user_id, current_user)
    moved = {
        field: value
        for field, value in (
            ("is_active", data.is_active),
            ("is_superuser", data.is_superuser),
            ("can_create_projects", data.can_create_projects),
        )
        if value is not None and getattr(user, field) != value
    }
    for field, value in moved.items():
        setattr(user, field, value)
    if moved.get("is_active") is False:
        await revoke_account_keys(session, user.id)
    await session.commit()
    if moved:
        await revoke_user_tokens(user.id)
    logger.info(
        "user updated",
        user=str(user.id),
        active=data.is_active,
        superuser=data.is_superuser,
        can_create_projects=data.can_create_projects,
        by=str(current_user.id),
    )
    await session.refresh(user)
    return (await read_users(session, [user]))[0]


@router.put("/{user_id}/projects", response_model=UserRead)
async def set_user_projects(
    user_id: UUID,
    data: UserProjects,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentSuperuser,
):
    """Replace the projects a user opens."""
    user = await _other_user(session, user_id, current_user)
    project_ids = await _known_projects(session, data.project_ids)
    moved = await replace_members(session, user.id, project_ids, current_user.id)
    await session.commit()
    if moved:
        await revoke_user_tokens(user.id)
    logger.info(
        "user projects set",
        user=str(user.id),
        projects=len(project_ids),
        by=str(current_user.id),
    )
    return (await read_users(session, [user]))[0]


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
            detail="Invalid user ID.",
        ) from e

    if uuid_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The signed-in account cannot be deleted.",
        )

    result = await session.execute(select(User).where(User.id == uuid_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    username = user.username
    await session.execute(
        update(ScanEngine)
        .where(ScanEngine.created_by == user.id, ScanEngine.builtin.is_(True))
        .values(created_by=current_user.id)
    )
    await session.delete(user)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{username} created records on this instance. Disable the account instead.",
        ) from e

    logger.info("user deleted", user=str(uuid_id), by=str(current_user.id))
    return {"message": f"User {username} deleted"}
