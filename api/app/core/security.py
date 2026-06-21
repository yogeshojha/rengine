import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.config import settings

TOKEN_TYPE_ACCESS = "access"  # noqa: S105
TOKEN_TYPE_REFRESH = "refresh"  # noqa: S105
TOKEN_TYPE_MFA = "mfa"  # noqa: S105

ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except (VerifyMismatchError, VerificationError):
        return False


def create_token(
    subject: str | Any,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    expire = datetime.now(UTC) + expires_delta
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": token_type,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


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
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        return None
