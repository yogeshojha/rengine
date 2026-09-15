from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.domain_posture import DEFAULT_DKIM_SELECTORS
from stages.config import StageConfig, advanced

MAX_SELECTORS = 60
MAX_SELECTOR_LENGTH = 63


class DnsPostureConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Domain posture",
        description="SPF, DMARC, DKIM, MTA-STS, DNSSEC and CAA read from each zone.",
    )
    dkim_selectors: list[str] = advanced(
        default_factory=lambda: list(DEFAULT_DKIM_SELECTORS),
        title="DKIM selectors probed",
        description="Selector names queried under _domainkey.",
        max_length=MAX_SELECTORS,
    )

    @field_validator("dkim_selectors")
    @classmethod
    def _clean_selectors(cls, values: list[str]) -> list[str]:
        seen: list[str] = []
        for raw in values:
            value = str(raw).strip().lower().strip(".")
            if value and len(value) <= MAX_SELECTOR_LENGTH and value not in seen:
                seen.append(value)
        return seen
