import base64
import secrets
from io import BytesIO

import pyotp
import qrcode
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from shared.logging import get_logger
from shared.models.user import User
from shared.redis import async_client
from shared.utils.crypto import decrypt_secret, encrypt_secret
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_ISSUER = "reNgine"
_BACKUP_CODE_COUNT = 10
_STEP_OFFSETS = (-1, 0, 1)
_USED_STEP_TTL = 120


def _backup_code() -> str:
    raw = secrets.token_hex(4)
    return f"{raw[:4]}-{raw[4:]}"


async def _claim_step(user: User, step: int) -> bool:
    """True once per user and time step."""
    try:
        claimed = await async_client().set(
            f"totp:used:{user.id}:{step}", "1", nx=True, ex=_USED_STEP_TTL
        )
    except Exception as exc:
        logger.warning("totp replay guard unavailable", error=str(exc))
        return True
    return bool(claimed)


def _qr_data_uri(otpauth_uri: str) -> str:
    img = qrcode.make(otpauth_uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


class TOTPService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_setup(self, user: User) -> dict:
        if user.totp_enabled:
            msg = "2FA is enabled. Disable it before enrolling again."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        secret = pyotp.random_base32()
        user.totp_secret_encrypted = encrypt_secret(secret)
        user.updated_at = utc_now()
        self.session.add(user)
        await self.session.commit()
        otpauth_uri = pyotp.TOTP(secret).provisioning_uri(
            name=user.username, issuer_name=_ISSUER
        )
        return {
            "secret": secret,
            "otpauth_uri": otpauth_uri,
            "qr": _qr_data_uri(otpauth_uri),
        }

    async def verify_and_enable(self, user: User, code: str) -> list[str]:
        if user.totp_enabled:
            msg = "2FA is enabled. Disable it before enrolling again."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        secret = self._require_secret(user)
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            msg = "Invalid verification code."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        codes = [_backup_code() for _ in range(_BACKUP_CODE_COUNT)]
        user.totp_enabled = True
        user.totp_backup_codes = [hash_password(c) for c in codes]
        user.updated_at = utc_now()
        self.session.add(user)
        await self.session.commit()
        return codes

    async def disable(self, user: User, code: str) -> None:
        if not await self.verify_code(user, code):
            msg = "Invalid verification code."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        user.totp_secret_encrypted = None
        user.totp_enabled = False
        user.totp_backup_codes = None
        user.updated_at = utc_now()
        self.session.add(user)
        await self.session.commit()

    async def verify_code(self, user: User, code: str) -> bool:
        if not user.totp_enabled or not user.totp_secret_encrypted:
            return False
        try:
            secret = decrypt_secret(user.totp_secret_encrypted)
        except ValueError:
            if await self._consume_backup_code(user, code):
                return True
            raise
        totp = pyotp.TOTP(secret)
        step = totp.timecode(utc_now())
        for offset in _STEP_OFFSETS:
            if pyotp.utils.strings_equal(str(code), totp.generate_otp(step + offset)):
                return await _claim_step(user, step + offset)
        return await self._consume_backup_code(user, code)

    async def _consume_backup_code(self, user: User, code: str) -> bool:
        locked = await self.session.scalar(
            select(User)
            .where(User.id == user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked is None:
            return False
        stored = locked.totp_backup_codes or []
        for i, hashed in enumerate(stored):
            if verify_password(code, hashed):
                locked.totp_backup_codes = [h for j, h in enumerate(stored) if j != i]
                locked.updated_at = utc_now()
                self.session.add(locked)
                await self.session.commit()
                return True
        return False

    def _require_secret(self, user: User) -> str:
        if not user.totp_secret_encrypted:
            msg = "2FA setup has not been started."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        return decrypt_secret(user.totp_secret_encrypted)
