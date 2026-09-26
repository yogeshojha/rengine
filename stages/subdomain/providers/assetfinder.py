from __future__ import annotations

from shared.enums.subdomain import SubdomainSource
from shared.services.proxy_resolve import proxy_env
from stages.subdomain.providers.base import SubdomainProvider


class AssetfinderProvider(SubdomainProvider):
    tool = "assetfinder"
    source = SubdomainSource.ASSETFINDER
    binary = "assetfinder"

    def discover(self) -> set[str]:
        result = self.run_tool(
            ["--subs-only", self.ctx.domain],
            use_output_file=False,
            silent=False,
            env=proxy_env(self.ctx.proxy_url),
        )
        return {line.strip() for line in result.output_lines if line.strip()}
