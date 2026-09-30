"""What names a row of each dimension, and the seed a focused run takes from it."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from shared.definitions.rescan import SeedKind
from shared.definitions.surface import SurfaceDimension
from shared.models.endpoint import Endpoint
from shared.models.secret import Secret
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability
from shared.utils.net import host_port


@dataclass(frozen=True)
class Identity:
    columns: Callable[[Any], list]
    key: Callable[[Any], str]
    label: Callable[[Any], str]
    detail: Callable[[Any], str]
    seed: Callable[[Any], str | None]
    seed_kind: str
    severity: Callable[[Any], str | None] = lambda _r: None


def _text(*parts: object) -> str:
    return " · ".join(str(p) for p in parts if p not in (None, ""))


def _host_seed(value: str | None) -> str | None:
    return value or None


def seed_kind_of(kind: str, value: str) -> str:
    """An address seed whatever the dimension says, when the value is one."""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return kind
    return SeedKind.ADDRESS.value


IDENTITIES: dict[str, Identity] = {
    SurfaceDimension.WEB_ASSETS.value: Identity(
        columns=lambda _s: [
            Subdomain.name,
            Subdomain.http_status,
            Subdomain.page_title,
        ],
        key=lambda r: r.name,
        label=lambda r: r.name,
        detail=lambda r: _text(r.http_status, r.page_title),
        seed=lambda r: _host_seed(r.name),
        seed_kind=SeedKind.HOST.value,
    ),
    SurfaceDimension.ENDPOINTS.value: Identity(
        columns=lambda _s: [
            Endpoint.signature,
            Endpoint.url,
            Endpoint.status_code,
            Endpoint.host,
        ],
        key=lambda r: r.signature,
        label=lambda r: r.url,
        detail=lambda r: _text(r.status_code),
        seed=lambda r: r.url or None,
        seed_kind=SeedKind.URL.value,
    ),
    SurfaceDimension.SERVICES.value: Identity(
        columns=lambda d: [
            d.c.ip,
            d.c.port,
            d.c.protocol,
            d.c.service_name,
            d.c.product,
        ],
        key=lambda r: f"{host_port(r.ip, r.port)}/{r.protocol}",
        label=lambda r: host_port(r.ip, r.port),
        detail=lambda r: _text(r.service_name, r.product),
        seed=lambda r: r.ip or None,
        seed_kind=SeedKind.ADDRESS.value,
    ),
    SurfaceDimension.IPS.value: Identity(
        columns=lambda d: [d.c.ip, d.c.asn_org, d.c.country],
        key=lambda r: r.ip,
        label=lambda r: r.ip,
        detail=lambda r: _text(r.asn_org, r.country),
        seed=lambda r: r.ip or None,
        seed_kind=SeedKind.ADDRESS.value,
    ),
    SurfaceDimension.VULNERABILITIES.value: Identity(
        columns=lambda _s: [
            Vulnerability.fingerprint,
            Vulnerability.template_name,
            Vulnerability.severity,
            Vulnerability.host,
            Vulnerability.ip,
        ],
        key=lambda r: r.fingerprint,
        label=lambda r: r.template_name,
        detail=lambda r: _text(r.severity, r.host or r.ip),
        seed=lambda r: r.host or r.ip or None,
        seed_kind=SeedKind.HOST.value,
        severity=lambda r: r.severity,
    ),
    SurfaceDimension.SOFTWARE.value: Identity(
        columns=lambda _s: [
            SoftwareCve.fingerprint,
            SoftwareCve.cve,
            SoftwareCve.name,
            SoftwareCve.version,
            SoftwareCve.host,
            SoftwareCve.ip,
            SoftwareCve.severity,
        ],
        key=lambda r: r.fingerprint,
        label=lambda r: r.cve,
        detail=lambda r: _text(f"{r.name} {r.version}".strip(), r.host or r.ip),
        seed=lambda r: r.host or r.ip or None,
        seed_kind=SeedKind.HOST.value,
        severity=lambda r: r.severity,
    ),
    SurfaceDimension.SECRETS.value: Identity(
        columns=lambda _s: [Secret.fingerprint, Secret.kind, Secret.host, Secret.url],
        key=lambda r: r.fingerprint,
        label=lambda r: r.kind,
        detail=lambda r: _text(r.host),
        seed=lambda r: _host_seed(r.host),
        seed_kind=SeedKind.HOST.value,
    ),
}


def identity(dimension: str) -> Identity:
    return IDENTITIES[dimension]


__all__ = ["IDENTITIES", "Identity", "identity", "seed_kind_of"]
