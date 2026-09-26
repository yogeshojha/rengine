from __future__ import annotations

from shared.enums.subdomain import SubdomainSource
from shared.services.proxy_resolve import is_socks5
from stages.subdomain.providers.base import SubdomainProvider


class TlsxProvider(SubdomainProvider):
    """TLS certificate SAN extraction via tlsx (cert-transparency style discovery)."""

    tool = "tlsx"
    source = SubdomainSource.TLSX
    binary = "tlsx"

    def availability(self) -> tuple[bool, str | None]:
        ok, reason = super().availability()
        if ok and self.ctx.proxy_url and not is_socks5(self.ctx.proxy_url):
            return (
                False,
                "tlsx takes a socks5 proxy. This scan's proxy cannot carry it.",
            )
        return ok, reason

    def discover(self) -> set[str]:
        args = ["-san", "-resp-only"]
        if self.ctx.proxy_url:
            args += ["-proxy", self.ctx.proxy_url]
        result = self.run_tool(args, input_data=[self.ctx.domain])
        return {line.strip() for line in result.output_lines if line.strip()}
