from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.scan_surface import MAX_REQUESTS, MAX_REQUESTS_PER_ORIGIN
from shared.definitions.vulnerabilities import (
    DEFAULT_SEVERITIES,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    reject_unknown,
)
from stages.config import StageConfig, advanced


class DastScanConfig(StageConfig):
    enabled: bool = Field(
        default=False,
        title="Fuzz discovered requests",
        description="Send payloads to the parameters this scan discovered.",
    )
    scanners: list[str] = Field(
        default_factory=lambda: ["nuclei"],
        title="Fuzzers",
        description="Tools that fuzz a request.",
        json_schema_extra={
            "options": ["nuclei", "dalfox"],
            "option_labels": {"nuclei": "Nuclei", "dalfox": "Dalfox"},
        },
    )
    severities: list[str] = Field(
        default_factory=lambda: list(DEFAULT_SEVERITIES),
        title="Severities",
        description="Severities to run.",
        json_schema_extra={
            "options": list(SEVERITY_ORDER),
            "option_labels": dict(SEVERITY_LABELS),
            "widget": "severity",
        },
    )
    directories: bool = Field(
        default=False,
        title="Directory exposure checks",
        description="Run the exposure checks under each discovered directory.",
    )
    headless: bool = Field(
        default=False,
        title="Browser fuzzing",
        description="Run the fuzzing checks that need a rendered page. Most DAST checks do.",
    )
    max_minutes: int = Field(
        default=30,
        ge=0,
        le=1440,
        title="Time budget (min)",
        description="Stop starting batches after this many minutes. 0 means no limit.",
    )
    max_requests_per_origin: int = advanced(
        MAX_REQUESTS_PER_ORIGIN,
        ge=1,
        le=1000,
        title="Requests per origin",
        description="Parameter sets fuzzed per origin at most.",
    )
    max_requests: int = advanced(
        MAX_REQUESTS,
        ge=1,
        le=20000,
        title="Request budget",
        description="Parameter sets fuzzed in one scan at most.",
    )
    interactsh: bool = advanced(
        False,
        title="Out-of-band testing",
        description="Detect blind injection through callbacks. The server is set on the vulnerability scan.",
    )

    @field_validator("severities")
    @classmethod
    def _known_severities(cls, value: list[str]) -> list[str]:
        return reject_unknown(value, SEVERITY_ORDER, "severity")
