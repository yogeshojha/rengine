import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

_DEFAULT_SECRET = "change-me-in-production-use-openssl-rand-hex-32"  # noqa: S105


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
