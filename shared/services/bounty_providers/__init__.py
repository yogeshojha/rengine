from __future__ import annotations

from sqlalchemy.orm import Session

from shared.services.bounty_providers.base import (
    AccessDeniedError,
    BountyProvider,
    BountyProviderError,
    CredentialsError,
)
from shared.services.bounty_providers.hackerone import HackerOneProvider
from shared.services.bounty_providers.intigriti import IntigritiProvider

PROVIDERS: tuple[type[BountyProvider], ...] = (HackerOneProvider, IntigritiProvider)

PROVIDERS_BY_PLATFORM: dict[str, type[BountyProvider]] = {
    p.platform: p for p in PROVIDERS
}


def provider_for(session: Session, platform: str) -> BountyProvider | None:
    """The configured provider for one platform, or None."""
    cls = PROVIDERS_BY_PLATFORM.get(platform)
    return cls.from_session(session) if cls else None


def configured_providers(session: Session) -> list[BountyProvider]:
    """Every platform this instance holds a credential for."""
    built = (cls.from_session(session) for cls in PROVIDERS)
    return [p for p in built if p is not None]


__all__ = [
    "PROVIDERS",
    "PROVIDERS_BY_PLATFORM",
    "AccessDeniedError",
    "BountyProvider",
    "BountyProviderError",
    "CredentialsError",
    "HackerOneProvider",
    "IntigritiProvider",
    "configured_providers",
    "provider_for",
]
