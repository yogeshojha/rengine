from __future__ import annotations

from pydantic import Field

from shared.definitions.wordlists import WordlistKind
from stages.config import StageConfig, rate, threads, wordlist


class VhostConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Virtual host bruteforce",
        description="Host-header fuzzing to surface vhosts not resolvable via DNS.",
    )
    wordlist: str = wordlist(
        WordlistKind.VHOST.value,
        title="Wordlist",
        description="Which list of host names to try. Custom lists are uploaded in the Tools Arsenal.",
    )
    threads: int = threads(30, title="Threads")
    rate: int = rate(150, tool="ffuf", title="Requests/s")
