"""Census and coverage predicates for scans."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import exists, select

from shared.definitions.surface import SURFACE_KINDS, SURFACE_ORDER, SurfaceDimension
from shared.definitions.vulnerabilities import Scanner
from shared.enums.scan import ScanActivityStatus, ScanScope, StageRole
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity


def census_only(model=Scan):
    """Runs that describe a target's whole surface."""
    return model.scope == ScanScope.FULL.value


@lru_cache(maxsize=1)
def producing_stages() -> dict[str, frozenset[str]]:
    """Dimension -> every stage that can write its rows."""
    from stages.registry import stages  # noqa: PLC0415

    out: dict[str, set[str]] = {key: set() for key in SURFACE_ORDER}
    for spec in stages():
        for key, kinds in SURFACE_KINDS.items():
            if spec.produces & kinds:
                out[key].add(spec.name)
    return {key: frozenset(names) for key, names in out.items()}


@lru_cache(maxsize=1)
def covering_stages() -> dict[str, frozenset[str]]:
    """Dimension -> the stages whose success means the dimension was scanned."""
    from stages.registry import stages  # noqa: PLC0415

    capability = {s.name for s in stages() if s.role == StageRole.CAPABILITY.value}
    always = {s.name for s in stages() if s.always_on}
    producing = producing_stages()
    out = {key: (names & capability) or names for key, names in producing.items()}
    software = SurfaceDimension.SOFTWARE.value
    out[software] = producing[software] & (capability | always)
    return out


def covers(model, dimension: str):
    """The scan wrote covering rows for the dimension, or a covering stage succeeded."""
    rows = select(1).where(model.scan_id == Scan.id)
    if dimension == SurfaceDimension.VULNERABILITIES.value:
        rows = rows.where(model.scanner != Scanner.RENGINE.value)
    return exists(rows) | exists(
        select(1).where(
            ScanActivity.scan_id == Scan.id,
            ScanActivity.status == ScanActivityStatus.SUCCESS.value,
            ScanActivity.name.in_(covering_stages()[dimension]),
        )
    )
