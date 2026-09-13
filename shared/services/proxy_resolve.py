import json

from shared.models.proxy import Proxy, ProxyEndpoint
from shared.utils.crypto import decrypt_stored


def load_proxy_endpoints(proxy: Proxy) -> list[ProxyEndpoint]:
    raw = decrypt_stored(proxy.endpoints_encrypted or "", label=f"Proxy {proxy.name!r}")
    if not raw:
        return []
    return [ProxyEndpoint(**e) for e in json.loads(raw)]


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
    if ep.username:
        cred = f"{ep.username}:{ep.password}@" if ep.password else f"{ep.username}@"
        return f"{ep.scheme}://{cred}{ep.host}:{ep.port}"
    return f"{ep.scheme}://{ep.host}:{ep.port}"


def resolve_proxy_url(proxy: Proxy | None) -> str | None:
    if proxy is None or not proxy.is_active:
        return None
    endpoints = load_proxy_endpoints(proxy)
    if not endpoints:
        return None
    return build_proxy_url(endpoints[0])
