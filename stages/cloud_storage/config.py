from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.cloud_storage import (
    DEFAULT_WORDS,
    MAX_WORD_LENGTH,
    MAX_WORDS,
)
from shared.services.cloud_storage import clean_words
from stages.config import StageConfig, advanced

# One request per candidate per provider; the clouds throttle well below the target ceiling.
PROBE_RATE_CAP = 20
PROBE_THREAD_CAP = 24


class CloudStorageConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Cloud storage",
        description="Find storage buckets named after the target and report which are open.",
    )
    guess: bool = Field(
        default=True,
        title="Guess bucket names",
        description="Try the target's name joined with common words, not only names the scan found.",
    )
    words: list[str] = advanced(
        default_factory=lambda: list(DEFAULT_WORDS),
        title="Words",
        description="Words joined to the name: example-backup, example-assets.",
        max_length=MAX_WORDS,
    )

    @field_validator("words")
    @classmethod
    def _clean_words(cls, values: list[str]) -> list[str]:
        return clean_words(values, max_length=MAX_WORD_LENGTH)
