from __future__ import annotations

import json
import urllib.request

from shared.enums.subdomain import SubdomainSource
from stages.subdomain.providers.base import SubdomainProvider

_CRTSH_URL = "https://crt.sh/?q=%25.{domain}&output=json"
_MAX_BYTES = 32 * 1024 * 1024


class CtfrProvider(SubdomainProvider):
    """Certificate Transparency enumeration via crt.sh (the CTFR data source)."""

    tool = "ctfr"
    source = SubdomainSource.CTFR
    binary = None

    def discover(self) -> set[str]:
        url = _CRTSH_URL.format(domain=self.ctx.domain)
        req = urllib.request.Request(url)  # noqa: S310
        with self._opener().open(req, timeout=self.ctx.timeout) as resp:
            raw = resp.read(_MAX_BYTES + 1)

        payload = raw[:_MAX_BYTES].decode("utf-8", errors="replace")
        if len(raw) > _MAX_BYTES:
            payload = payload.rpartition("},")[0] + "}]"
            self._cut = True
            self._note = f"stopped reading at {_MAX_BYTES // (1024 * 1024)} MB"

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
