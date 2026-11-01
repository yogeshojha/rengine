from __future__ import annotations

from dataclasses import dataclass, field

from shared.definitions.ports import MAX_PORT
from tools.banner.signatures import readable

MAX_PRODUCT = 200
MAX_VERSION = 100
MAX_CPES = 10
TCP = "tcp"


@dataclass(frozen=True)
class IndexedService:
    port: int
    tls: bool = False
    product: str | None = None
    version: str | None = None
    banner: str | None = None
    cpe: list[str] = field(default_factory=list)


def _text(value, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value and len(value) <= limit else None


def _cpes(item: dict) -> list[str]:
    raw = item.get("cpe23") or item.get("cpe") or []
    if not isinstance(raw, list):
        return []
    return [c for c in raw if isinstance(c, str) and c][:MAX_CPES]


def parse_host(payload: dict | None) -> list[IndexedService]:
    """The TCP services in a Shodan host record, one per port."""
    if not isinstance(payload, dict):
        return []
    services: dict[int, IndexedService] = {}
    for item in payload.get("data") or []:
        if not isinstance(item, dict):
            continue
        port = item.get("port")
        if (
            not isinstance(port, int)
            or isinstance(port, bool)
            or not 0 < port <= MAX_PORT
        ):
            continue
        if (item.get("transport") or TCP) != TCP:
            continue
        data = item.get("data")
        service = IndexedService(
            port=port,
            tls="ssl" in item,
            product=_text(item.get("product"), MAX_PRODUCT),
            version=_text(item.get("version"), MAX_VERSION),
            banner=readable(data.encode("utf-8", "replace"))
            if isinstance(data, str)
            else None,
            cpe=_cpes(item),
        )
        known = services.get(port)
        if known is None or (service.product and not known.product):
            services[port] = service
    return [services[p] for p in sorted(services)]
