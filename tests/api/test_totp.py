from __future__ import annotations

import uuid

import pytest

from app.core.security import hash_password
from app.services.totp import TOTPService
from shared.models.user import User

pytestmark = pytest.mark.api

BACKUP = "abcd-1234"


async def _unreadable(session) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"totp{tag}",
        email=f"totp{tag}@test.local",
        hashed_password=hash_password("Vq7#mT9!pLx2@wRz"),
        totp_enabled=True,
        totp_secret_encrypted="not-a-fernet-token",
        totp_backup_codes=[hash_password(BACKUP)],
    )
    session.add(user)
    await session.commit()
    return user


async def test_backup_code_passes_when_the_secret_is_unreadable(durable):
    user = await _unreadable(durable)

    assert await TOTPService(durable).verify_code(user, BACKUP) is True
    await durable.refresh(user)
    assert user.totp_backup_codes == []


async def test_wrong_code_with_an_unreadable_secret_raises(durable):
    user = await _unreadable(durable)

    with pytest.raises(ValueError, match="corrupted"):
        await TOTPService(durable).verify_code(user, "0000-0000")
