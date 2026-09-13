import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

_DEFAULT_SECRET = "change-me-in-production-use-openssl-rand-hex-32"  # noqa: S105

# a Fernet token opens with a 0x80 version byte and a zero-padded timestamp
_FERNET_PREFIX = "gAAAAA"


class SecretDecryptionError(RuntimeError):
    """A stored value is sealed but this instance's key cannot open it."""


def _fernet() -> Fernet:
    secret = os.environ.get("SECRET_KEY", _DEFAULT_SECRET)
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


def is_sealed(value: str) -> bool:
    """Whether a stored value carries a Fernet token."""
    return value.startswith(_FERNET_PREFIX)


def decrypt_stored(value: str, *, label: str) -> str:
    """Open a sealed value. A value written before sealing shipped is returned as it is."""
    if not is_sealed(value):
        return value
    try:
        return decrypt_secret(value)
    except ValueError as exc:
        msg = (
            f"{label} was sealed with a different SECRET_KEY and cannot be read. "
            "Restore the SECRET_KEY this instance was set up with, or enter the "
            "credential again."
        )
        raise SecretDecryptionError(msg) from exc
