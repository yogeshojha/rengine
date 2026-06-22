from __future__ import annotations

import json
import urllib.parse
import urllib.request

from engines.subdomain.providers.base import SubdomainProvider
from shared.enums.api_key import APIProvider
from shared.enums.subdomain import SubdomainSource

_NETLAS_URL = "https://app.netlas.io/api/domains/"
_MAX_RESULTS = 1000


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: ARG002
        return None


def _walk_domains(node: object, out: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "domain" and isinstance(value, str):
                out.add(value.strip())
            else:
                _walk_domains(value, out)
    elif isinstance(node, list):
        for item in node:
            _walk_domains(item, out)


class NetlasProvider(SubdomainProvider):
    tool = "netlas"
    source = SubdomainSource.NETLAS
    binary = None
    requires_key = APIProvider.NETLAS

    def discover(self) -> set[str]:
        key = self.ctx.api_keys.get(APIProvider.NETLAS.value)
        if not key:
            return set()
        query = urllib.parse.urlencode(
            {"q": f"domain:*.{self.ctx.domain}", "fields": "domain", "size": 100}
        )
        url = f"{_NETLAS_URL}?{query}"
        proxy = self.ctx.proxy_url
        opener = urllib.request.build_opener(
            _NoRedirect(),
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            if proxy
            else urllib.request.ProxyHandler({}),
        )
        req = urllib.request.Request(url, headers={"X-API-Key": key})  # noqa: S310
        with opener.open(req, timeout=self.ctx.timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return set()

        hosts: set[str] = set()
        _walk_domains(data.get("items", data), hosts)
        return set(list(hosts)[:_MAX_RESULTS])
