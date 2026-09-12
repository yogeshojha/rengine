from __future__ import annotations

from pydantic import Field

from shared.definitions.wordlists import WordlistKind
from stages.config import StageConfig, rate, threads, wordlist


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
    threads: int = threads(30, title="Threads")
    rate: int = rate(150, tool="ffuf", title="Requests/s")
