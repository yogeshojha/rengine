import asyncio
import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from starlette.concurrency import run_in_threadpool

from app.config import ALGORITHM, settings

TOKEN_TYPE_ACCESS = "access"  # noqa: S105
TOKEN_TYPE_REFRESH = "refresh"  # noqa: S105
TOKEN_TYPE_MFA = "mfa"  # noqa: S105

ACCESS_TOKEN_COOKIE = "access_token"  # noqa: S105
REFRESH_TOKEN_COOKIE = "refresh_token"  # noqa: S105
AUTH_COOKIES = (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE)
ISSUED_MS_CLAIM = "iat_ms"

ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# each hash holds 64 MB
HASH_CONCURRENCY = 4
_hash_slots = asyncio.Semaphore(HASH_CONCURRENCY)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except (VerifyMismatchError, VerificationError):
        return False


async def hash_password_async(password: str) -> str:
    async with _hash_slots:
        return await run_in_threadpool(hash_password, password)


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    async with _hash_slots:
        return await run_in_threadpool(verify_password, plain_password, hashed_password)


@cache
def signing_key() -> str:
    """JWT_SECRET_KEY, else a key derived from SECRET_KEY for this purpose alone."""
    if settings.JWT_SECRET_KEY:
        return settings.JWT_SECRET_KEY
    return hmac.new(
        settings.SECRET_KEY.encode(), b"rengine/jwt", hashlib.sha256
    ).hexdigest()


def create_token(
    subject: str | Any,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    expire = now + expires_delta
    to_encode = {
        "exp": expire,
        "iat": int(now.timestamp()),
        ISSUED_MS_CLAIM: int(now.timestamp() * 1000),
        "sub": str(subject),
        "type": token_type,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(to_encode, signing_key(), algorithm=ALGORITHM)


def create_access_token(subject: str | Any) -> str:
    return create_token(
        subject=subject,
        token_type=TOKEN_TYPE_ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str | Any) -> str:
    return create_token(
        subject=subject,
        token_type=TOKEN_TYPE_REFRESH,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            signing_key(),
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type", "jti"]},
        )
    except jwt.PyJWTError:
        return None
