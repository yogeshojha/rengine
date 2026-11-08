from __future__ import annotations

from pydantic import Field

from shared.definitions.wordlists import WordlistKind
from stages.config import StageConfig, advanced, wordlist


class ContentDiscoveryConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Guess paths and files",
        description="Request wordlist paths on every web asset. One request per word per web asset.",
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
        description="Words tried per web asset, from the top of the list.",
    )
    max_minutes: int = Field(
        default=20,
        ge=1,
        le=480,
        title="Time budget (min)",
        description="Stop after this many minutes. Web assets cut short are reported.",
    )
    max_hosts: int = advanced(
        25,
        ge=1,
        le=1_000,
        title="Web assets to guess against",
        description="Web assets that answered are picked first.",
    )
