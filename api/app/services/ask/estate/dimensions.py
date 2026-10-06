"""The dimensions estate answers read, and how each is searched."""

from __future__ import annotations

from mcp.dimensions import Dimension, by_key
from shared.definitions.asset_query import SOFTWARE_QUERY
from shared.definitions.surface import SURFACE_ORDER, SurfaceDimension

SOFTWARE = Dimension(
    key=SurfaceDimension.SOFTWARE.value,
    registry=SOFTWARE_QUERY,
    tab="software",
    service_path="app.services.software.SoftwareService",
)

DIMENSIONS: dict[str, Dimension] = {
    key: dim
    for key in SURFACE_ORDER
    if (dim := (SOFTWARE if key == SOFTWARE.key else by_key().get(key))) is not None
}

# dimensions whose rows Ask shows
ROW_DIMENSIONS: frozenset[str] = frozenset(DIMENSIONS) - {
    SurfaceDimension.SECRETS.value
}
# no groups() on the service
UNGROUPED: frozenset[str] = frozenset({SurfaceDimension.SOFTWARE.value})


def groupable(key: str) -> bool:
    return key in DIMENSIONS and key not in UNGROUPED
