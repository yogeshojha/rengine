from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from app.services import access_keys
from shared.models.access_key import AccessKeyCreate, AccessKeyCreated, AccessKeyRead
from shared.models.user import User

router = APIRouter(tags=["access-keys"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/access-keys", response_model=list[AccessKeyRead])
async def list_own_keys(current_user: CurrentUser, session: Session):
    return await access_keys.list_keys(session, current_user.id)


@router.post(
    "/access-keys",
    response_model=AccessKeyCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_key(
    data: AccessKeyCreate, current_user: CurrentUser, session: Session
):
    return await access_keys.create_key(session, current_user, data)


@router.delete("/access-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_own_key(key_id: UUID, current_user: CurrentUser, session: Session):
    await access_keys.revoke_key(session, current_user.id, key_id, by=current_user.id)


async def _user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return user


@router.get("/users/{user_id}/access-keys", response_model=list[AccessKeyRead])
async def list_user_keys(user_id: UUID, _admin: CurrentSuperuser, session: Session):
    user = await _user(session, user_id)
    return await access_keys.list_keys(session, user.id)


@router.delete(
    "/users/{user_id}/access-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_user_key(
    user_id: UUID, key_id: UUID, admin: CurrentSuperuser, session: Session
):
    user = await _user(session, user_id)
    await access_keys.revoke_key(session, user.id, key_id, by=admin.id)
