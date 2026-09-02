from __future__ import annotations

from shared.enums.subdomain import SubdomainSource
from stages.subdomain.providers.base import SubdomainProvider, proxy_env
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError


class Sublist3rProvider(SubdomainProvider):
    tool = "sublist3r"
    source = SubdomainSource.SUBLIST3R
    binary = "sublist3r"

    def discover(self) -> set[str]:
        runner = CLIToolRunner(self.binary, default_timeout=self.ctx.timeout)
        try:
            result = runner.run(
                args=["-d", self.ctx.domain, "-t", str(self.ctx.threads)],
                use_output_file=True,
                output_flag="-o",
                output_format=OutputFormat.PLAIN,
                silent=False,
                timeout=self.ctx.timeout,
                env=proxy_env(self.ctx.proxy_url),
                recorder=self.ctx.recorder,
                tool=self.tool,
                extra_args=self.extra_args,
            )
        except ToolNotFoundError:
            return set()
        return {line.strip() for line in result.output_lines if line.strip()}
