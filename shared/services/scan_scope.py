"""A focused rescan is evidence, not a census — every surface rollup filters on this."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import exists, select

from shared.definitions.surface import SURFACE_KINDS, SURFACE_ORDER
from shared.enums.scan import ScanActivityStatus, ScanScope
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity


def census_only(model=Scan):
    """Runs that describe a target's whole surface."""
    return model.scope == ScanScope.FULL.value


@lru_cache(maxsize=1)
def covering_stages() -> dict[str, frozenset[str]]:
    """Dimension -> the stage names whose success means the dimension was scanned."""
    from stages.registry import stages  # noqa: PLC0415

    out: dict[str, set[str]] = {key: set() for key in SURFACE_ORDER}
    for spec in stages():
        for key, kinds in SURFACE_KINDS.items():
            if spec.produces & kinds:
                out[key].add(spec.name)
    return {key: frozenset(names) for key, names in out.items()}


def covers(model, dimension: str, scan=Scan):
    """The scan wrote rows for the dimension, or a producing stage succeeded."""
    return exists(select(1).where(model.scan_id == scan.id)) | exists(
        select(1).where(
            ScanActivity.scan_id == scan.id,
            ScanActivity.status == ScanActivityStatus.SUCCESS.value,
            ScanActivity.name.in_(covering_stages()[dimension]),
        )
    )
