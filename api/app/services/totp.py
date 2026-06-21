import base64
import secrets
from io import BytesIO

import pyotp
import qrcode
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.security import hash_password, verify_password
from shared.models.user import User
from shared.utils.datetime import utc_now

_ISSUER = "reNgine"
_BACKUP_CODE_COUNT = 10


def _backup_code() -> str:
    raw = secrets.token_hex(4)
    return f"{raw[:4]}-{raw[4:]}"


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
            msg = "2FA is already enabled. Disable it first to re-enroll."
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
            msg = "2FA is already enabled. Disable it first to re-enroll."
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
        secret = decrypt_secret(user.totp_secret_encrypted)
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            return True
        return await self._consume_backup_code(user, code)

    async def _consume_backup_code(self, user: User, code: str) -> bool:
        stored = user.totp_backup_codes or []
        for i, hashed in enumerate(stored):
            if verify_password(code, hashed):
                user.totp_backup_codes = [h for j, h in enumerate(stored) if j != i]
                user.updated_at = utc_now()
                self.session.add(user)
                await self.session.commit()
                return True
        return False

    def _require_secret(self, user: User) -> str:
        if not user.totp_secret_encrypted:
            msg = "2FA setup has not been started."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        return decrypt_secret(user.totp_secret_encrypted)
