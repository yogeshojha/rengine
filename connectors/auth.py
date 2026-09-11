"""Token minting and verification."""

from __future__ import annotations

import hashlib
import secrets

PREFIX = "rngconn_"
SECRET_BYTES = 24
DISPLAY_CHARS = 8


def mint() -> tuple[str, str, str]:
    """Return (secret, sha256 hash, display prefix)."""
    body = secrets.token_hex(SECRET_BYTES)
    secret = f"{PREFIX}{body}"
    return secret, fingerprint(secret), f"{PREFIX}{body[:DISPLAY_CHARS]}"


def fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.strip().encode()).hexdigest()


def looks_like_token(value: str) -> bool:
    return value.startswith(PREFIX) and len(value) == len(PREFIX) + SECRET_BYTES * 2


def from_header(value: str | None) -> str | None:
    """Accept `Bearer <token>` or a bare token."""
    if not value:
        return None
    candidate = value.strip()
    scheme, _, rest = candidate.partition(" ")
    if scheme.lower() == "bearer" and rest.strip():
        candidate = rest.strip()
    return candidate or None
