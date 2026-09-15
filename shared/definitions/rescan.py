"""What a rescan of each result dimension seeds and re-runs."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.surface import SurfaceDimension
from shared.enums.subdomain import SubdomainSource


class SeedKind(StrEnum):
    HOST = "host"
    ADDRESS = "address"
    URL = "url"


MAX_RUN_ASSETS = 5000
MAX_RUN_SCANS = 25
RESCAN_LABEL = "Rescan"
ASSET_SEED_STAGE = "asset_seed"
RESCAN_SOURCE = "rescan"
SEED_SOURCES: tuple[str, ...] = (RESCAN_SOURCE, SubdomainSource.IMPORTED.value)

# the seed a row of each dimension contributes
DIMENSION_SEED: dict[str, str] = {
    SurfaceDimension.WEB_ASSETS.value: SeedKind.HOST.value,
    SurfaceDimension.ENDPOINTS.value: SeedKind.HOST.value,
    SurfaceDimension.SERVICES.value: SeedKind.ADDRESS.value,
    SurfaceDimension.IPS.value: SeedKind.ADDRESS.value,
    SurfaceDimension.VULNERABILITIES.value: SeedKind.HOST.value,
    SurfaceDimension.SECRETS.value: SeedKind.HOST.value,
}

DIMENSION_STAGES: dict[str, tuple[str, ...]] = {
    SurfaceDimension.WEB_ASSETS.value: ("http_probe",),
    SurfaceDimension.ENDPOINTS.value: ("http_probe", "url_discovery"),
    SurfaceDimension.SERVICES.value: ("port_scan",),
    SurfaceDimension.IPS.value: ("port_scan",),
    SurfaceDimension.VULNERABILITIES.value: ("http_probe", "vulnerability_scan"),
    SurfaceDimension.SECRETS.value: ("http_probe", "secret_mining"),
}

RESCANNABLE_STAGES: frozenset[str] = frozenset(
    {
        "http_probe",
        "port_scan",
        "url_discovery",
        "vulnerability_scan",
        "secret_mining",
        "screenshot",
        "vhost",
    }
)

# the dimension a recheck change belongs to; anything else is the web asset itself
CHANGE_DIMENSION: dict[str, str] = {
    "ports": SurfaceDimension.SERVICES.value,
    "findings": SurfaceDimension.VULNERABILITIES.value,
    "endpoints": SurfaceDimension.ENDPOINTS.value,
    "resolved_ips": SurfaceDimension.IPS.value,
}


def change_dimension(field: str) -> str:
    return CHANGE_DIMENSION.get(field, SurfaceDimension.WEB_ASSETS.value)


SEED_KIND_NOUN: dict[str, tuple[str, str]] = {
    SeedKind.HOST.value: ("host", "hosts"),
    SeedKind.ADDRESS.value: ("address", "addresses"),
    SeedKind.URL.value: ("URL", "URLs"),
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
