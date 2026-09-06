"""The five result dimensions a scan produces, named as the UI names them."""

from __future__ import annotations

from enum import StrEnum

from shared.enums.scan import AssetKind


class SurfaceDimension(StrEnum):
    WEB_ASSETS = "web_assets"
    ENDPOINTS = "endpoints"
    SERVICES = "services"
    IPS = "ips"
    VULNERABILITIES = "vulnerabilities"


SURFACE_ORDER: tuple[str, ...] = tuple(d.value for d in SurfaceDimension)

SURFACE_LABELS: dict[str, str] = {
    SurfaceDimension.WEB_ASSETS.value: "Web assets",
    SurfaceDimension.ENDPOINTS.value: "Endpoints",
    SurfaceDimension.SERVICES.value: "Services",
    SurfaceDimension.IPS.value: "IPs",
    SurfaceDimension.VULNERABILITIES.value: "Vulnerabilities",
}

SURFACE_NOUN: dict[str, tuple[str, str]] = {
    SurfaceDimension.WEB_ASSETS.value: ("web asset", "web assets"),
    SurfaceDimension.ENDPOINTS.value: ("endpoint", "endpoints"),
    SurfaceDimension.SERVICES.value: ("service", "services"),
    SurfaceDimension.IPS.value: ("address", "addresses"),
    SurfaceDimension.VULNERABILITIES.value: ("finding", "findings"),
}

# a stage covers a dimension when it produces one of these kinds
SURFACE_KINDS: dict[str, frozenset[str]] = {
    SurfaceDimension.WEB_ASSETS.value: frozenset(
        {AssetKind.HOSTS.value, AssetKind.HTTP_ASSETS.value}
    ),
    SurfaceDimension.ENDPOINTS.value: frozenset({AssetKind.ENDPOINTS.value}),
    SurfaceDimension.SERVICES.value: frozenset({AssetKind.PORTS.value}),
    SurfaceDimension.IPS.value: frozenset({AssetKind.ADDRESSES.value}),
    SurfaceDimension.VULNERABILITIES.value: frozenset(
        {AssetKind.VULNERABILITIES.value}
    ),
}
