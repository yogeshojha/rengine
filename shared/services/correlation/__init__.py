"""One definition of a shared identity, for every scope that asks."""

from __future__ import annotations

from shared.services.correlation.hubs import (
    CorrelationFinder,
    Hub,
    HubSet,
    Member,
    hub_label,
)
from shared.services.correlation.kinds import (
    KINDS,
    KindSpec,
    asset_join,
    platform_for,
    values_carried,
)

__all__ = [
    "KINDS",
    "CorrelationFinder",
    "Hub",
    "HubSet",
    "KindSpec",
    "Member",
    "asset_join",
    "hub_label",
    "platform_for",
    "values_carried",
]
