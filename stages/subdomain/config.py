from __future__ import annotations

from pydantic import Field

from shared.definitions.wordlists import WordlistKind
from shared.enums.scan import Intensity
from stages.config import StageConfig, wordlist
from stages.subdomain.providers import PASSIVE_PROVIDERS

PASSIVE_TOOLS: tuple[str, ...] = tuple(
    sorted({cls.tool for cls in PASSIVE_PROVIDERS.values()})
)
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


def tool_timeout(intensity: str) -> int:
    """Seconds a passive source may run under this intensity."""
    return _TOOL_TIMEOUTS.get(intensity, _TOOL_TIMEOUTS[Intensity.NORMAL.value])


class SubdomainConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Subdomain discovery",
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

    @property
    def enabled_sources(self) -> list[str]:
        return [tool for tool in self.passive_tools if tool in PASSIVE_PROVIDERS]


PERMUTATION_SEEDS = 250
PERMUTATION_LIMIT = 20_000
DNS_BATCH_SIZE = 1000
DNS_BATCH_CONCURRENCY = 1
DNS_IDLE_TIMEOUT = 90
