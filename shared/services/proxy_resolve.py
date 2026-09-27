import json
import secrets
from urllib.parse import urlsplit

from sqlalchemy import select

from shared.models.proxy import Proxy, ProxyEndpoint
from shared.utils.crypto import decrypt_stored
from shared.utils.net import host_port


def load_proxy_endpoints(proxy: Proxy) -> list[ProxyEndpoint]:
    raw = decrypt_stored(proxy.endpoints_encrypted or "", label=f"Proxy {proxy.name!r}")
    if not raw:
        return []
    return [ProxyEndpoint(**e) for e in json.loads(raw)]


SOCKS_SCHEMES = frozenset({"socks5", "socks5h"})


def is_socks5(proxy_url: str | None) -> bool:
    """Whether a tool that speaks only socks5 can carry this proxy."""
    if not proxy_url:
        return False
    raw = proxy_url if "://" in proxy_url else f"socks5://{proxy_url}"
    return urlsplit(raw).scheme.lower() in SOCKS_SCHEMES


def proxy_env(proxy_url: str | None) -> dict[str, str] | None:
    """Proxy env vars honoured by Go HTTP clients that take no proxy flag."""
    if not proxy_url:
        return None
    return {
        "HTTP_PROXY": proxy_url,
        "HTTPS_PROXY": proxy_url,
        "ALL_PROXY": proxy_url,
    }


def build_proxy_url(ep: ProxyEndpoint) -> str:
    authority = host_port(ep.host, ep.port)
    if ep.username:
        cred = f"{ep.username}:{ep.password}@" if ep.password else f"{ep.username}@"
        return f"{ep.scheme}://{cred}{authority}"
    return f"{ep.scheme}://{authority}"


def resolve_proxy_url(proxy: Proxy | None) -> str | None:
    """One endpoint per scan, drawn from the pool when the proxy holds several."""
    if proxy is None or not proxy.is_active:
        return None
    endpoints = load_proxy_endpoints(proxy)
    if not endpoints:
        return None
    return build_proxy_url(secrets.choice(endpoints))


def default_proxy(session) -> Proxy | None:
    return (
        session.execute(
            select(Proxy).where(Proxy.is_default.is_(True), Proxy.is_active.is_(True))
        )
        .scalars()
        .first()
    )


def scan_proxy_url(session, context) -> str | None:
    """The context's proxy, or the default proxy for a scan without a context."""
    if context is None:
        return resolve_proxy_url(default_proxy(session))
    if context.proxy_id is None:
        return None
    return resolve_proxy_url(session.get(Proxy, context.proxy_id))
