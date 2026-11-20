"""Access keys: create, list, revoke, authenticate and record use."""

from __future__ import annotations

import math
import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import API_V1_PREFIX
from app.core.ratelimit import record_failure, too_many_attempts
from shared.definitions.access_keys import (
    ACCESS_KEY_PREFIX,
    CALLS_KEY,
    FAILURE_KEY,
    FAILURE_LIMIT,
    FAILURE_WINDOW_SECONDS,
    INVALID_DETAIL,
    LAST_USE_SECONDS,
    LIMIT_DETAIL,
    MAX_ACCESS_KEYS,
    OWNER_KEY,
    OWNER_SECONDS,
    USED_KEY,
)
from shared.definitions.api_reference import first_request
from shared.logging import get_logger
from shared.models.access_key import (
    AccessKey,
    AccessKeyCreate,
    AccessKeyCreated,
    AccessKeyRead,
)
from shared.models.user import User
from shared.redis import async_client, state_available, state_failed
from shared.utils.bearer import TokenFormat, fingerprint
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

ACCESS_KEY_FORMAT = TokenFormat(ACCESS_KEY_PREFIX)
NOT_FOUND = "Access key not found."


def invalid_key() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=INVALID_DETAIL,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _redis():
    return async_client() if state_available() else None


def _active(user_id: uuid.UUID):
    now = utc_now()
    return (
        AccessKey.user_id == user_id,
        AccessKey.revoked_at.is_(None),
        (AccessKey.expires_at.is_(None)) | (AccessKey.expires_at > now),
    )


async def _pending_calls(keys: list[AccessKey]) -> dict[uuid.UUID, int]:
    client = _redis()
    if client is None or not keys:
        return {}
    try:
        raw = await client.mget([CALLS_KEY.format(key_id=k.id) for k in keys])
    except Exception as exc:
        state_failed(exc)
        return {}
    return {k.id: int(v) for k, v in zip(keys, raw, strict=True) if v}


def read(key: AccessKey, pending: int = 0) -> AccessKeyRead:
    now = utc_now()
    return AccessKeyRead(
        id=key.id,
        name=key.name,
        prefix=key.prefix,
        access=key.access,
        expires_at=key.expires_at,
        expired=key.expires_at is not None and key.expires_at <= now,
        last_used_at=key.last_used_at,
        last_used_ip=key.last_used_ip,
        use_count=key.use_count + pending,
        created_at=key.created_at,
    )


async def list_keys(session: AsyncSession, user_id: uuid.UUID) -> list[AccessKeyRead]:
    keys = list(
        (
            await session.scalars(
                select(AccessKey)
                .where(AccessKey.user_id == user_id, AccessKey.revoked_at.is_(None))
                .order_by(AccessKey.created_at.desc())
            )
        ).all()
    )
    pending = await _pending_calls(keys)
    return [read(k, pending.get(k.id, 0)) for k in keys]


async def create_key(
    session: AsyncSession, user: User, data: AccessKeyCreate
) -> AccessKeyCreated:
    await session.execute(select(User.id).where(User.id == user.id).with_for_update())
    held = await session.scalar(
        select(func.count()).select_from(AccessKey).where(*_active(user.id))
    )
    if held >= MAX_ACCESS_KEYS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=LIMIT_DETAIL)
    secret, token_hash, prefix = ACCESS_KEY_FORMAT.mint()
    now = utc_now()
    key = AccessKey(
        user_id=user.id,
        name=data.name,
        prefix=prefix,
        token_hash=token_hash,
        access=data.access,
        expires_at=(
            now + timedelta(days=data.expires_in_days)
            if data.expires_in_days is not None
            else None
        ),
        created_at=now,
    )
    session.add(key)
    await session.commit()
    logger.info(
        "access key created", user=str(user.id), key=str(key.id), access=key.access
    )
    return AccessKeyCreated(
        **read(key).model_dump(),
        key=secret,
        first_request=first_request(API_V1_PREFIX),
    )


async def _forget_owners(hashes: list[str]) -> None:
    client = _redis()
    if client is None or not hashes:
        return
    try:
        await client.delete(*(OWNER_KEY.format(token_hash=h) for h in hashes))
    except Exception as exc:
        state_failed(exc)


async def revoke_key(
    session: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID, *, by: uuid.UUID
) -> None:
    key = await session.scalar(
        select(AccessKey).where(
            AccessKey.id == key_id,
            AccessKey.user_id == user_id,
            AccessKey.revoked_at.is_(None),
        )
    )
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    key.revoked_at = utc_now()
    await session.commit()
    await _forget_owners([key.token_hash])
    logger.info("access key revoked", user=str(user_id), key=str(key_id), by=str(by))


async def revoke_account_keys(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Revoke every key of the account; the caller commits."""
    hashes = list(
        (
            await session.scalars(
                update(AccessKey)
                .where(AccessKey.user_id == user_id, AccessKey.revoked_at.is_(None))
                .values(revoked_at=utc_now())
                .returning(AccessKey.token_hash)
            )
        ).all()
    )
    await _forget_owners(hashes)
    if hashes:
        logger.info("access keys revoked", user=str(user_id), count=len(hashes))
    return len(hashes)


# ---------- authentication ----------


async def authenticate(
    session: AsyncSession, secret: str, address: str
) -> tuple[AccessKey, User]:
    """The key and its owner, or 401 with one body for every refusal."""
    failures = FAILURE_KEY.format(address=address)
    await too_many_attempts(failures, limit=FAILURE_LIMIT, fail_closed=True)
    found = None
    if ACCESS_KEY_FORMAT.looks_like_token(secret):
        found = (
            await session.execute(
                select(AccessKey, User)
                .join(User, User.id == AccessKey.user_id)
                .where(AccessKey.token_hash == fingerprint(secret))
            )
        ).first()
    now = utc_now()
    if (
        found is None
        or found[0].revoked_at is not None
        or (found[0].expires_at is not None and found[0].expires_at <= now)
        or not found[1].is_active
    ):
        await record_failure(failures, window_seconds=FAILURE_WINDOW_SECONDS)
        logger.warning(
            "access key refused",
            address=address,
            key=str(found[0].id) if found else None,
        )
        raise invalid_key()
    key, user = found
    await _mark_used(session, key, user, address)
    return key, user


def _owner_seconds(key: AccessKey) -> int:
    if key.expires_at is None:
        return OWNER_SECONDS
    left = math.ceil((key.expires_at - utc_now()).total_seconds())
    return max(1, min(OWNER_SECONDS, left))


async def _mark_used(
    session: AsyncSession, key: AccessKey, user: User, address: str
) -> None:
    client = _redis()
    if client is None:
        return
    calls = CALLS_KEY.format(key_id=key.id)
    try:
        if not await client.set(
            USED_KEY.format(key_id=key.id), "1", nx=True, ex=LAST_USE_SECONDS
        ):
            await client.incr(calls)
            return
        pending = int(await client.getdel(calls) or 0)
        await client.set(
            OWNER_KEY.format(token_hash=key.token_hash),
            str(user.id),
            ex=_owner_seconds(key),
        )
    except Exception as exc:
        state_failed(exc)
        logger.warning("access key use not recorded", key=str(key.id), error=str(exc))
        return
    now = utc_now()
    await session.execute(
        update(AccessKey)
        .where(AccessKey.id == key.id)
        .values(
            last_used_at=now,
            last_used_ip=address[:64],
            use_count=AccessKey.use_count + pending + 1,
        )
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    key.last_used_at = now
    key.last_used_ip = address[:64]
    key.use_count += pending + 1


async def owner_of(secret: str) -> str | None:
    """The owner the throttle charges for a key, while its last use is fresh."""
    if not ACCESS_KEY_FORMAT.looks_like_token(secret):
        return None
    client = _redis()
    if client is None:
        return None
    raw = await client.get(OWNER_KEY.format(token_hash=fingerprint(secret)))
    return str(raw) if raw else None
