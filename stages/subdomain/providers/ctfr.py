from __future__ import annotations

import json
import urllib.request

from shared.enums.subdomain import SubdomainSource
from stages.subdomain.providers.base import SubdomainProvider

_CRTSH_URL = "https://crt.sh/?q=%25.{domain}&output=json"


class CtfrProvider(SubdomainProvider):
    """Certificate Transparency enumeration via crt.sh (the CTFR data source)."""

    tool = "ctfr"
    source = SubdomainSource.CTFR
    binary = None

    def discover(self) -> set[str]:
        url = _CRTSH_URL.format(domain=self.ctx.domain)
        req = urllib.request.Request(url)  # noqa: S310
        with self._opener().open(req, timeout=self.ctx.timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")

        try:
            records = json.loads(payload)
        except json.JSONDecodeError:
            return set()

        hosts: set[str] = set()
        for rec in records:
            for field_name in ("name_value", "common_name"):
                raw = rec.get(field_name) or ""
                for line in raw.splitlines():
                    candidate = line.strip()
                    if candidate:
                        hosts.add(candidate)
        return hosts
