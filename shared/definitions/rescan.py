"""What a rescan of each result dimension seeds and re-runs."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.surface import SurfaceDimension


class SeedKind(StrEnum):
    HOST = "host"
    ADDRESS = "address"


MAX_SEED_ASSETS = 200
RESCAN_LABEL = "Rescan"
ASSET_SEED_STAGE = "asset_seed"

# the seed a row of each dimension contributes
DIMENSION_SEED: dict[str, str] = {
    SurfaceDimension.WEB_ASSETS.value: SeedKind.HOST.value,
    SurfaceDimension.ENDPOINTS.value: SeedKind.HOST.value,
    SurfaceDimension.SERVICES.value: SeedKind.ADDRESS.value,
    SurfaceDimension.IPS.value: SeedKind.ADDRESS.value,
    SurfaceDimension.VULNERABILITIES.value: SeedKind.HOST.value,
}

# what a one-click rescan re-runs; every consumer here is listed with what feeds it
DIMENSION_STAGES: dict[str, tuple[str, ...]] = {
    SurfaceDimension.WEB_ASSETS.value: ("http_probe",),
    SurfaceDimension.ENDPOINTS.value: ("http_probe", "url_discovery"),
    SurfaceDimension.SERVICES.value: ("port_scan",),
    SurfaceDimension.IPS.value: ("port_scan",),
    SurfaceDimension.VULNERABILITIES.value: ("http_probe", "vulnerability_scan"),
}

# stages a rescan may run at all: everything else needs a target rather than assets
RESCANNABLE_STAGES: frozenset[str] = frozenset(
    {
        "http_probe",
        "port_scan",
        "url_discovery",
        "vulnerability_scan",
        "screenshot",
        "vhost",
    }
)

SEED_KIND_NOUN: dict[str, tuple[str, str]] = {
    SeedKind.HOST.value: ("host", "hosts"),
    SeedKind.ADDRESS.value: ("address", "addresses"),
}


def seed_kind_for(dimension: str) -> str:
    return DIMENSION_SEED.get(dimension, SeedKind.HOST.value)


def stages_for(dimension: str) -> tuple[str, ...]:
    return DIMENSION_STAGES.get(dimension, ("http_probe",))


def rescan_label(dimension: str, count: int) -> str:
    from shared.definitions.surface import SURFACE_NOUN  # noqa: PLC0415

    singular, plural = SURFACE_NOUN.get(dimension, ("asset", "assets"))
    noun = singular if count == 1 else plural
    return f"{RESCAN_LABEL} · {count} {noun}"
