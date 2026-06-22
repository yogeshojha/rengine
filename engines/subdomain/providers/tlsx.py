from __future__ import annotations

from engines.subdomain.providers.base import SubdomainProvider
from shared.enums.subdomain import SubdomainSource
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError


class TlsxProvider(SubdomainProvider):
    """TLS certificate SAN extraction via tlsx (cert-transparency style discovery)."""

    tool = "tlsx"
    source = SubdomainSource.TLSX
    binary = "tlsx"

    def discover(self) -> set[str]:
        runner = CLIToolRunner(self.binary, default_timeout=self.ctx.timeout)
        try:
            result = runner.run(
                args=["-san", "-resp-only"],
                input_data=[self.ctx.domain],
                input_flag="-l",
                output_format=OutputFormat.PLAIN,
                silent=True,
                silent_flag="-silent",
                timeout=self.ctx.timeout,
            )
        except ToolNotFoundError:
            return set()
        return {line.strip() for line in result.output_lines if line.strip()}
