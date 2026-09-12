from __future__ import annotations

from pydantic import Field

from shared.definitions.wordlists import WordlistKind
from shared.enums.scan import Intensity
from stages.config import StageConfig, threads, timeout, wordlist
from stages.subdomain.providers import PASSIVE_PROVIDERS

PASSIVE_TOOLS: tuple[str, ...] = tuple(sorted(PASSIVE_PROVIDERS))
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
    enabled: bool = Field(
        default=True,
        title="Enabled",
        description="Enumerate subdomains from passive sources, certificates, wordlists and permutations.",
    )
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
    zone_transfer: bool = Field(
        default=True,
        title="Attempt zone transfer",
        description="Request the whole zone from each of its nameservers.",
    )
    bruteforce: bool = Field(
        default=True,
        title="Bruteforce names",
        description="Resolve wordlist names against the target's nameservers.",
    )
    wordlist: str = wordlist(
        WordlistKind.SUBDOMAIN.value,
        title="Wordlist",
        description="List to guess from. Custom lists are uploaded in the Arsenal.",
    )
    wordlist_limit: int = Field(
        default=1000,
        ge=100,
        le=1_000_000,
        title="Words to try",
        description="Names tried per apex, from the top of the list.",
    )
    permutations: bool = Field(
        default=False,
        title="Permute discovered names",
        description="Resolve variants of discovered names, such as api-dev and api2.",
    )
    permutation_seeds: int = Field(
        default=250,
        ge=1,
        le=10_000,
        title="Names to permute",
        description="Discovered names to build variants from.",
    )
    permutation_limit: int = Field(
        default=20_000,
        ge=100,
        le=500_000,
        title="Variants to resolve",
        description="Cap on generated variants.",
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
        description="Resolver invocations in flight at once. Above 1 only with dedicated resolvers.",
    )
    dns_idle_timeout: int = timeout(
        90,
        title="Resolver stall timeout",
        description="Abandon a resolver batch after this many seconds with no answer.",
    )

    @property
    def enabled_sources(self) -> list[str]:
        return [tool for tool in self.passive_tools if tool in PASSIVE_PROVIDERS]

    def tool_timeout(self, intensity: str) -> int:
        return _TOOL_TIMEOUTS.get(intensity, _TOOL_TIMEOUTS[Intensity.NORMAL.value])
