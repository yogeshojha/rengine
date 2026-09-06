"""A focused rescan is evidence, not a census — every surface rollup filters on this."""

from __future__ import annotations

from shared.enums.scan import ScanScope
from shared.models.scan import Scan


def census_only(model=Scan):
    """Runs that describe a target's whole surface."""
    return model.scope == ScanScope.FULL.value
