from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.scan_surface import (
    BASE_MAX_DEPTH,
    MAX_BASES_PER_ORIGIN,
    MAX_REQUESTS,
    MAX_REQUESTS_PER_ORIGIN,
)
from shared.definitions.vulnerabilities import (
    DEFAULT_SEVERITIES,
    MAX_FINDINGS_PER_SCAN,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    reject_unknown,
)
from stages.config import StageConfig, rate, threads, timeout


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
    max_requests_per_origin: int = Field(
        default=MAX_REQUESTS_PER_ORIGIN,
        ge=1,
        le=1000,
        title="Requests per origin",
        description="Parameter sets fuzzed per origin at most.",
    )
    max_requests: int = Field(
        default=MAX_REQUESTS,
        ge=1,
        le=20000,
        title="Request budget",
        description="Parameter sets fuzzed in one scan at most.",
    )
    directories: bool = Field(
        default=False,
        title="Directory exposure checks",
        description="Run the exposure checks under each discovered directory.",
    )
    max_dirs_per_origin: int = Field(
        default=MAX_BASES_PER_ORIGIN,
        ge=1,
        le=200,
        title="Directories per origin",
    )
    dir_depth: int = Field(
        default=BASE_MAX_DEPTH,
        ge=1,
        le=3,
        title="Directory depth",
        description="Deepest directory level checked.",
    )
    fuzz_param_frequency: int = Field(
        default=10,
        ge=1,
        le=100,
        title="Parameter patience",
        description="Sightings of one parameter name without a match before it is skipped on that host.",
    )
    rate: int = rate(50, tool="nuclei", title="Request rate (rps)")
    threads: int = threads(
        25, title="Concurrency", description="Checks running in parallel."
    )
    bulk_size: int = Field(default=25, ge=1, le=500, title="Requests per check")
    timeout: int = timeout(10, title="Request timeout (s)")
    retries: int = Field(default=1, ge=0, le=5, title="Retries")
    max_host_error: int = Field(
        default=30,
        ge=1,
        le=500,
        title="Host error budget",
        description="Errors a host may return before it is dropped.",
    )
    max_minutes: int = Field(
        default=30,
        ge=0,
        le=1440,
        title="Time budget (min)",
        description="Stop starting batches after this many minutes. 0 means no limit.",
    )
    waf_rate_divisor: int = Field(
        default=3,
        ge=1,
        le=20,
        title="WAF rate divisor",
        description="Hosts behind a WAF or CDN are fuzzed at the request rate divided by this. 1 disables.",
    )
    honeypot_threshold: int = Field(default=0, ge=0, le=200, title="Honeypot threshold")
    headless: bool = Field(
        default=False,
        title="Browser fuzzing",
        description="Run the fuzzing checks that need a rendered page. Most DAST checks do.",
    )
    interactsh: bool = Field(
        default=False,
        title="Out-of-band testing",
        description="Detect blind injection through callbacks to an external server.",
    )
    interactsh_server: str = Field(
        default="", max_length=200, title="Self-hosted OAST server"
    )
    oast_wait_minutes: int = Field(
        default=5, ge=0, le=120, title="Keep listening (minutes)"
    )
    store_evidence: bool = Field(
        default=True,
        title="Store request and response",
        description="Keep the request and response that produced each finding.",
    )
    max_evidence_recovery: int = Field(
        default=0, ge=0, le=2000, title="Evidence recovery budget"
    )
    max_findings: int = Field(
        default=MAX_FINDINGS_PER_SCAN,
        ge=1,
        le=MAX_FINDINGS_PER_SCAN,
        title="Finding budget",
    )

    @field_validator("severities")
    @classmethod
    def _known_severities(cls, value: list[str]) -> list[str]:
        return reject_unknown(value, SEVERITY_ORDER, "severity")
