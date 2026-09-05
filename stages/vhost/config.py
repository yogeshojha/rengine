from __future__ import annotations

from pydantic import Field

from stages.config import StageConfig, rate, threads

DEFAULT_WORDLIST = "/app/tools/data/vhosts.txt"


class VhostConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Virtual host bruteforce",
        description="Host-header fuzzing to surface vhosts not resolvable via DNS.",
    )
    wordlist: str = Field(
        default=DEFAULT_WORDLIST,
        title="Wordlist",
        description="Path to a vhost wordlist.",
    )
    threads: int = threads(30, title="Threads")
    rate: int = rate(150, tool="ffuf", title="Requests/s")
