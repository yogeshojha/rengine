from __future__ import annotations

from pydantic import Field

from shared.enums.scan import Intensity
from stages.config import StageConfig, threads, timeout
from stages.subdomain.providers import PASSIVE_PROVIDERS

PASSIVE_TOOLS: tuple[str, ...] = tuple(sorted(PASSIVE_PROVIDERS))
# ranked by real-world frequency, so a smaller budget is simply the first N lines
DEFAULT_WORDLIST = "/app/tools/data/subdomains.txt"
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
    bruteforce: bool = Field(
        default=True,
        title="Bruteforce names",
        description="Ask the target's nameservers for common names the public sources never listed.",
    )
    wordlist: str = Field(
        default=DEFAULT_WORDLIST,
        max_length=500,
        title="Wordlist",
        description="One label per line, ranked best first. The word budget below reads from the top.",
    )
    wordlist_limit: int = Field(
        default=1000,
        ge=100,
        le=1_000_000,
        title="Words to try",
        description="Names tried per apex, from the top of the list. This is a time budget: the resolver clears about 9 a second.",
    )
    permutations: bool = Field(
        default=False,
        title="Permute discovered names",
        description="Build variants of the names already found (api → api-dev, api2, api-staging) and resolve those too.",
    )
    permutation_seeds: int = Field(
        default=250,
        ge=1,
        le=10_000,
        title="Names to permute",
        description="How many discovered names to build variants from. Variants grow with the square of this.",
    )
    permutation_limit: int = Field(
        default=20_000,
        ge=100,
        le=500_000,
        title="Variants to resolve",
        description="Cap on generated variants. Each one is a DNS query, on top of the word budget.",
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
