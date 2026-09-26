from __future__ import annotations

from shared.enums.api_key import APIProvider
from shared.enums.subdomain import SubdomainSource
from shared.services.proxy_resolve import proxy_env
from stages.subdomain.providers.base import SubdomainProvider


class GithubProvider(SubdomainProvider):
    """Subdomains written into public code, which no other source reads."""

    tool = "github-subdomains"
    source = SubdomainSource.GITHUB
    binary = "github-subdomains"
    requires_key = APIProvider.GITHUB

    def discover(self) -> set[str]:
        # the token goes in the environment, so it never reaches the command log
        env = dict(proxy_env(self.ctx.proxy_url) or {})
        env["GITHUB_TOKEN"] = self.ctx.api_keys.get(APIProvider.GITHUB.value, "")
        result = self.run_tool(
            ["-d", self.ctx.domain, "-raw", "-q"],
            use_output_file=False,
            silent=False,
            env=env,
        )
        suffix = f".{self.ctx.domain}"
        return {
            host
            for line in result.output_lines
            if (host := line.strip().lower())
            and (host == self.ctx.domain or host.endswith(suffix))
        }
