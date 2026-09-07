import ipaddress
from functools import lru_cache

from starlette.requests import Request

from app.config import settings

UNKNOWN = "unknown"


@lru_cache(maxsize=1)
def _trusted() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    nets = []
    for raw in settings.TRUSTED_PROXIES.split(","):
        entry = raw.strip()
        if not entry:
            continue
        try:
            nets.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            continue
    return tuple(nets)


def _is_trusted(host: str) -> bool:
    nets = _trusted()
    if not nets:
        return False
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(addr in net for net in nets)


def client_id(request: Request) -> str:
    """The furthest-out address we are willing to believe, walking X-Forwarded-For right to left."""
    peer = request.client.host if request.client else UNKNOWN
    if not _is_trusted(peer):
        return peer
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",")]
    for hop in reversed([h for h in hops if h]):
        if not _is_trusted(hop):
            return hop
    return peer
