from __future__ import annotations

from pydantic import Field

from shared.enums.scan import Intensity
from stages.config import StageConfig, threads, timeout
from stages.subdomain.providers import PASSIVE_PROVIDERS

PASSIVE_TOOLS: tuple[str, ...] = tuple(sorted(PASSIVE_PROVIDERS))
# amass is deliberately not here: it never exits early, so it costs the whole
# tool timeout on every scan for hosts the other sources already return
DEFAULT_PASSIVE_TOOLS: list[str] = [
    "subfinder",
    "ctfr",
    "crtname",
    "assetfinder",
]

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
    dns_batch_size: int = Field(
        default=1000,
        ge=100,
        le=20000,
        title="Resolver batch size",
        description="Names sent to the resolver per invocation.",
    )
    dns_batch_concurrency: int = Field(
        default=1,
        ge=1,
        le=8,
        title="Resolver batches in parallel",
        description=(
            "Resolver invocations in flight at once. Leave this at 1 unless you run your "
            "own resolvers: on public resolvers three batches at once answered 446 of the "
            "same 1,000 names that one batch answered 838 of. The loss is uniform across "
            "batches, so the stall and peer-median checks cannot see it."
        ),
    )
    dns_idle_timeout: int = timeout(
        90,
        title="Resolver stall timeout",
        description=(
            "Abandon a resolver batch after this many seconds with no answer. "
            "Resolution is not capped by total runtime — a resolver that keeps "
            "answering keeps running, however many names there are."
        ),
    )

    @property
    def enabled_sources(self) -> list[str]:
        return [tool for tool in self.passive_tools if tool in PASSIVE_PROVIDERS]

    def tool_timeout(self, intensity: str) -> int:
        return _TOOL_TIMEOUTS.get(intensity, _TOOL_TIMEOUTS[Intensity.NORMAL.value])
