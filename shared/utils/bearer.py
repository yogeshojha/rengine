"""Bearer token minting and verification."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

SECRET_BYTES = 24
DISPLAY_CHARS = 8


def fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.strip().encode()).hexdigest()


def from_header(value: str | None) -> str | None:
    """Accept `Bearer <token>` or a bare token."""
    if not value:
        return None
    candidate = value.strip()
    scheme, _, rest = candidate.partition(" ")
    if scheme.lower() == "bearer" and rest.strip():
        candidate = rest.strip()
    return candidate or None


@dataclass(frozen=True)
class TokenFormat:
    prefix: str

    def mint(self) -> tuple[str, str, str]:
        """Return (secret, sha256 hash, display prefix)."""
        body = secrets.token_hex(SECRET_BYTES)
        secret = f"{self.prefix}{body}"
        return secret, fingerprint(secret), f"{self.prefix}{body[:DISPLAY_CHARS]}"

    def looks_like_token(self, value: str) -> bool:
        return (
            value.startswith(self.prefix)
            and len(value) == len(self.prefix) + SECRET_BYTES * 2
        )
