import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from shared.config import base_settings


class SecretDecryptionError(RuntimeError):
    """A stored value is sealed but this instance's key cannot open it."""


def _fernet() -> Fernet:
    secret = base_settings().SECRET_KEY
    if not secret:
        msg = "SECRET_KEY is not set. Generate one with: openssl rand -hex 32"
        raise RuntimeError(msg)
    key = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        msg = "Invalid or corrupted secret token"
        raise ValueError(msg) from exc


def try_decrypt(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        return decrypt_secret(token)
    except ValueError:
        return None


def decrypt_stored(value: str, *, label: str) -> str:
    """Open a sealed value."""
    if not value:
        return ""
    try:
        return decrypt_secret(value)
    except ValueError as exc:
        msg = (
            f"{label} was sealed with a different SECRET_KEY and cannot be read. "
            "Restore the SECRET_KEY this instance was set up with, or enter the "
            "credential again."
        )
        raise SecretDecryptionError(msg) from exc
