from __future__ import annotations

from pydantic import Field

from shared.definitions.wordlists import WordlistKind
from stages.config import StageConfig, rate, threads, timeout, wordlist


class ContentDiscoveryConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Guess paths and files",
        description="Request wordlist paths on every live site. One request per word per site.",
    )
    wordlist: str = wordlist(
        WordlistKind.CONTENT.value,
        title="Wordlist",
        description="List to guess from. Custom lists are uploaded in the Arsenal.",
    )
    wordlist_limit: int = Field(
        default=1000,
        ge=50,
        le=200_000,
        title="Words to try",
        description="Words tried per site, from the top of the list.",
    )
    max_hosts: int = Field(
        default=25,
        ge=1,
        le=1_000,
        title="Sites to guess against",
        description="Sites tried. Sites that answered are picked first.",
    )
    max_minutes: int = Field(
        default=20,
        ge=1,
        le=480,
        title="Time budget (minutes)",
        description="The run stops after this many minutes and reports partial coverage.",
    )
    threads: int = threads(40, title="Threads")
    rate: int = rate(50, tool="ffuf", title="Requests/s")
    timeout: int = timeout(8, title="Request timeout (s)")
