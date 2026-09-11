from __future__ import annotations

from pydantic import Field

from shared.definitions.wordlists import WordlistKind
from stages.config import StageConfig, rate, threads, timeout, wordlist


class ContentDiscoveryConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Guess paths and files",
        description="Ask every live site for the paths a wordlist says are common. This sends one request per word per site.",
    )
    wordlist: str = wordlist(
        WordlistKind.CONTENT.value,
        title="Wordlist",
        description="Which list to guess from. Custom lists are uploaded in the Tools Arsenal.",
    )
    wordlist_limit: int = Field(
        default=1000,
        ge=50,
        le=200_000,
        title="Words to try",
        description="Words tried per site, from the top of the list. The list is ranked, so a smaller budget is simply the first N.",
    )
    max_hosts: int = Field(
        default=25,
        ge=1,
        le=1_000,
        title="Sites to guess against",
        description="Requests are words x sites, so this is the other half of the budget. Sites that answered are picked first.",
    )
    max_minutes: int = Field(
        default=20,
        ge=1,
        le=480,
        title="Time budget (minutes)",
        description="The run stops here and reports what it found, however much of the wordlist it reached.",
    )
    threads: int = threads(40, title="Threads")
    rate: int = rate(50, tool="ffuf", title="Requests/s")
    timeout: int = timeout(8, title="Request timeout (s)")
