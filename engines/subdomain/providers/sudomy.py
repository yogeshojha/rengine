from __future__ import annotations

from engines.subdomain.providers.base import SubdomainProvider
from shared.enums.subdomain import SubdomainSource


class SudomyProvider(SubdomainProvider):
    """Scaffold: implements the provider interface; enumeration not yet wired."""

    tool = "sudomy"
    source = SubdomainSource.SUDOMY
    binary = "sudomy"

    def availability(self) -> tuple[bool, str | None]:
        return False, "sudomy provider scaffolded — not yet enabled"

    def discover(self) -> set[str]:
        return set()
