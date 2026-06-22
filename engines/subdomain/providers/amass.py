from __future__ import annotations

import math

from engines.subdomain.providers.base import SubdomainProvider
from shared.enums.subdomain import SubdomainSource
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError


class AmassProvider(SubdomainProvider):
    """Passive subdomain enumeration via amass enum -passive."""

    tool = "amass"
    source = SubdomainSource.AMASS
    binary = "amass"

    def discover(self) -> set[str]:
        runner = CLIToolRunner(self.binary, default_timeout=self.ctx.timeout)
        timeout_min = max(1, math.ceil(self.ctx.timeout / 60))
        try:
            result = runner.run(
                args=[
                    "enum",
                    "-passive",
                    "-d",
                    self.ctx.domain,
                    "-nocolor",
                    "-timeout",
                    str(timeout_min),
                ],
                output_format=OutputFormat.PLAIN,
                silent=False,
                timeout=self.ctx.timeout,
            )
        except ToolNotFoundError:
            return set()
        return {line.strip() for line in result.output_lines if line.strip()}
