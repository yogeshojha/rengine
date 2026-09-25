from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.lookalikes import DEFAULT_WORDS
from stages.config import StageConfig, advanced

MAX_WORDS = 50
MAX_WORD_LENGTH = 30


class LookalikeDomainsConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Lookalike domains",
        description="Registered typo, homoglyph and TLD variants of the target's domain.",
    )
    tld_swap: bool = Field(
        default=True,
        title="Other TLDs",
        description="Check the same name under common TLDs.",
    )
    page_similarity: bool = Field(
        default=True,
        title="Page comparison",
        description="Fetch each lookalike's page and compare it to the target's.",
    )
    registration: bool = Field(
        default=True,
        title="Registration date",
        description="Read the registrar and creation date over RDAP.",
    )
    words: list[str] = advanced(
        default_factory=lambda: list(DEFAULT_WORDS),
        title="Words",
        description="Words joined to the name: login-example.com, examplelogin.com.",
        max_length=MAX_WORDS,
    )

    @field_validator("words")
    @classmethod
    def _clean_words(cls, values: list[str]) -> list[str]:
        seen: list[str] = []
        for raw in values:
            value = "".join(
                c for c in str(raw).strip().lower() if c.isalnum() or c == "-"
            )
            if value and len(value) <= MAX_WORD_LENGTH and value not in seen:
                seen.append(value)
        return seen
