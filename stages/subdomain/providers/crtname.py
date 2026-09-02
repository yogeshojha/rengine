from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request

from shared.enums.subdomain import SubdomainSource
from stages.subdomain.providers.base import SubdomainProvider

_CRTNAME_URL = "https://crt.name/v1/search"
_USER_AGENT = "reNgine/3.0 (+https://rengine.wiki)"
_APEX_HINT_RE = re.compile(r"eTLD\+1 is ([a-z0-9.-]+)", re.IGNORECASE)
_MAX_BYTES = 32 * 1024 * 1024
_BAD_APEX = 400


class CrtNameProvider(SubdomainProvider):
    """Certificate Transparency index via crt.name (keyless, 100 requests per IP per day)."""

    tool = "crtname"
    source = SubdomainSource.CRTNAME
    binary = None

    def discover(self) -> set[str]:
        body = self._fetch(self.ctx.domain)
        return {line.strip() for line in body.splitlines() if line.strip()}

    def _fetch(self, apex: str, *, retry_apex: bool = True) -> str:
        query = urllib.parse.urlencode({"apex": apex})
        proxy = self.ctx.proxy_url
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            if proxy
            else urllib.request.ProxyHandler({})
        )
        req = urllib.request.Request(  # noqa: S310
            f"{_CRTNAME_URL}?{query}", headers={"User-Agent": _USER_AGENT}
        )
        try:
            with opener.open(req, timeout=self.ctx.timeout) as resp:
                raw = resp.read(_MAX_BYTES + 1)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace").strip()
            hint = _APEX_HINT_RE.search(detail)
            # the endpoint only accepts an eTLD+1 but names it when it rejects a subdomain
            if e.code == _BAD_APEX and retry_apex and hint and hint.group(1) != apex:
                return self._fetch(hint.group(1), retry_apex=False)
            message = f"crt.name {e.code}: {detail[:200]}"
            raise RuntimeError(message) from e

        body = raw[:_MAX_BYTES].decode("utf-8", errors="replace")
        return body.rpartition("\n")[0] if len(raw) > _MAX_BYTES else body
