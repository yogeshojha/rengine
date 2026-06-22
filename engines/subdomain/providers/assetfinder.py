from __future__ import annotations

from engines.subdomain.providers.base import SubdomainProvider
from shared.enums.subdomain import SubdomainSource
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError


class AssetfinderProvider(SubdomainProvider):
    tool = "assetfinder"
    source = SubdomainSource.ASSETFINDER
    binary = "assetfinder"

    def discover(self) -> set[str]:
        runner = CLIToolRunner(self.binary, default_timeout=self.ctx.timeout)
        try:
            result = runner.run(
                args=["--subs-only", self.ctx.domain],
                use_output_file=False,
                output_format=OutputFormat.PLAIN,
                silent=False,
                timeout=self.ctx.timeout,
            )
        except ToolNotFoundError:
            return set()
        return {line.strip() for line in result.output_lines if line.strip()}
