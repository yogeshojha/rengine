from __future__ import annotations

import math
import re

from shared.enums.subdomain import SubdomainSource
from shared.services.proxy_resolve import proxy_env
from stages.subdomain.providers.base import SubdomainProvider

_FQDN_RE = re.compile(r"([A-Za-z0-9_.-]+) \(FQDN\)")


class AmassProvider(SubdomainProvider):
    """Passive subdomain enumeration via amass enum -passive."""

    tool = "amass"
    source = SubdomainSource.AMASS
    binary = "amass"

    def discover(self) -> set[str]:
        timeout_min = max(1, math.ceil(self.ctx.timeout / 60))
        result = self.run_tool(
            [
                "enum",
                "-passive",
                "-d",
                self.ctx.domain,
                "-nocolor",
                "-timeout",
                str(timeout_min),
            ],
            silent=False,
            env=proxy_env(self.ctx.proxy_url),
        )
        names: set[str] = set()
        for line in result.output_lines:
            names.update(_FQDN_RE.findall(line))
        return names
