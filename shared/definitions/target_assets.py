"""Target web asset list: states and sorts."""

from __future__ import annotations

from enum import StrEnum


class AssetState(StrEnum):
    ALL = "all"
    CURRENT = "current"
    NEW = "new"
    GONE = "gone"


class AssetSort(StrEnum):
    NAME = "name"
    FIRST_SEEN = "first_seen"
    LAST_SEEN = "last_seen"
    SCANS = "scans"
    STATUS = "status"


ASSET_STATES: tuple[str, ...] = tuple(s.value for s in AssetState)
ASSET_SORTS: tuple[str, ...] = tuple(s.value for s in AssetSort)
