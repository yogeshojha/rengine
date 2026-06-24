import json

from shared.models.proxy import Proxy, ProxyEndpoint
from shared.utils.crypto import try_decrypt


def load_proxy_endpoints(proxy: Proxy) -> list[ProxyEndpoint]:
    raw = try_decrypt(proxy.endpoints_encrypted)
    if not raw:
        return []
    return [ProxyEndpoint(**e) for e in json.loads(raw)]


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
