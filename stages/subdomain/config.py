from __future__ import annotations

from pydantic import Field

from shared.enums.scan import Intensity
from stages.config import StageConfig, threads
from stages.subdomain.providers import PASSIVE_PROVIDERS

PASSIVE_TOOLS: tuple[str, ...] = tuple(sorted(PASSIVE_PROVIDERS))
DEFAULT_PASSIVE_TOOLS: list[str] = ["subfinder", "ctfr", "assetfinder", "amass"]

_TOOL_TIMEOUTS = {
    Intensity.PASSIVE.value: 240,
    Intensity.NORMAL.value: 360,
    Intensity.AGGRESSIVE.value: 600,
}


class SubdomainConfig(StageConfig):
    passive_tools: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PASSIVE_TOOLS),
        title="Passive sources",
        description="Public sources to query for subdomains.",
        json_schema_extra={"options": list(PASSIVE_TOOLS)},
    )
    tls_discovery: bool = Field(
        default=True,
        title="TLS certificate discovery",
        description="Pull subject alternative names from the target's certificates.",
    )
    dns_threads: int = threads(30, title="Resolver threads")

    @property
    def enabled_sources(self) -> list[str]:
        return [tool for tool in self.passive_tools if tool in PASSIVE_PROVIDERS]

    def tool_timeout(self, intensity: str) -> int:
        return _TOOL_TIMEOUTS.get(intensity, _TOOL_TIMEOUTS[Intensity.NORMAL.value])
