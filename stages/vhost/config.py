from __future__ import annotations

from pydantic import Field

from shared.definitions.wordlists import WordlistKind
from stages.config import StageConfig, wordlist


class VhostConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Virtual host bruteforce",
        description="Find virtual hosts that DNS does not resolve, by varying the Host header.",
    )
    wordlist: str = wordlist(
        WordlistKind.VHOST.value,
        title="Wordlist",
        description="List of host names to try. Custom lists are uploaded in the Arsenal.",
    )


BUDGET_SECONDS_PER_IP = 600
