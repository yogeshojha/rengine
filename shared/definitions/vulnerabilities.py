from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_TEMPLATE_BYTES = 512_000
MAX_TEMPLATE_UPLOAD = 50
MAX_SELECTED_TEMPLATES = 2000
MAX_FINDINGS_PER_SCAN = 20_000
MAX_EVIDENCE_BYTES = 100_000

OFFICIAL_ROOT = "/app/vuln-templates/official"
CUSTOM_ROOT = "/app/vuln-templates/custom"
TEMPLATE_REPO = "https://github.com/projectdiscovery/nuclei-templates"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


SEVERITY_ORDER: tuple[str, ...] = tuple(s.value for s in Severity)

SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(SEVERITY_ORDER)}

SEVERITY_LABELS: dict[str, str] = {
    Severity.CRITICAL.value: "Critical",
    Severity.HIGH.value: "High",
    Severity.MEDIUM.value: "Medium",
    Severity.LOW.value: "Low",
    Severity.INFO.value: "Info",
    Severity.UNKNOWN.value: "Unknown",
}

SEVERITY_HELP: dict[str, str] = {
    Severity.CRITICAL.value: "Exploitable now, with system or data compromise as the outcome.",
    Severity.HIGH.value: "Direct path to compromise, usually needing one more condition.",
    Severity.MEDIUM.value: "Meaningful weakness that raises the cost of the next finding.",
    Severity.LOW.value: "Hygiene defect with limited standalone impact.",
    Severity.INFO.value: "An observation about the asset, not a weakness.",
    Severity.UNKNOWN.value: "The check did not state a severity.",
}

ACTIONABLE_SEVERITIES: tuple[str, ...] = (
    Severity.CRITICAL.value,
    Severity.HIGH.value,
    Severity.MEDIUM.value,
)

ALERT_SEVERITIES: tuple[str, ...] = (Severity.CRITICAL.value, Severity.HIGH.value)

DEFAULT_SEVERITIES: list[str] = [
    Severity.CRITICAL.value,
    Severity.HIGH.value,
    Severity.MEDIUM.value,
    Severity.LOW.value,
]


def severity_rank(value: str | None) -> int:
    return SEVERITY_RANK.get(
        (value or "").lower(), SEVERITY_RANK[Severity.UNKNOWN.value]
    )


def coerce_severity(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in SEVERITY_RANK else Severity.UNKNOWN.value


class VulnState(StrEnum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED = "accepted"


VULN_STATES: tuple[str, ...] = tuple(s.value for s in VulnState)

VULN_STATE_LABELS: dict[str, str] = {
    VulnState.OPEN.value: "Open",
    VulnState.CONFIRMED.value: "Confirmed",
    VulnState.FALSE_POSITIVE.value: "False positive",
    VulnState.ACCEPTED.value: "Risk accepted",
}

VULN_STATE_HELP: dict[str, str] = {
    VulnState.OPEN.value: "Not yet reviewed.",
    VulnState.CONFIRMED.value: "Reviewed and reproduced.",
    VulnState.FALSE_POSITIVE.value: "Reviewed and rejected. Suppressed on later scans of this target.",
    VulnState.ACCEPTED.value: "Reviewed and accepted. Kept out of the alerting path.",
}

SUPPRESSED_STATES: tuple[str, ...] = (
    VulnState.FALSE_POSITIVE.value,
    VulnState.ACCEPTED.value,
)


class CorroborationBasis(StrEnum):
    CVE = "cve"
    CWE = "cwe"


CORROBORATION_BASIS_LABELS: dict[str, str] = {
    CorroborationBasis.CVE.value: "Names the same CVE",
    CorroborationBasis.CWE.value: "Names the same weakness class",
}


class Scanner(StrEnum):
    NUCLEI = "nuclei"


SCANNER_LABELS: dict[str, str] = {Scanner.NUCLEI.value: "Nuclei"}

DEFAULT_SCANNERS: list[str] = [Scanner.NUCLEI.value]


class Protocol(StrEnum):
    HTTP = "http"
    NETWORK = "network"
    DNS = "dns"
    SSL = "ssl"
    FILE = "file"
    HEADLESS = "headless"
    JAVASCRIPT = "javascript"
    WEBSOCKET = "websocket"
    WHOIS = "whois"
    OTHER = "other"


PROTOCOLS: tuple[str, ...] = tuple(p.value for p in Protocol)

PROTOCOL_LABELS: dict[str, str] = {
    Protocol.HTTP.value: "HTTP",
    Protocol.NETWORK.value: "Network",
    Protocol.DNS.value: "DNS",
    Protocol.SSL.value: "TLS",
    Protocol.FILE.value: "File",
    Protocol.HEADLESS.value: "Browser",
    Protocol.JAVASCRIPT.value: "JavaScript",
    Protocol.WEBSOCKET.value: "WebSocket",
    Protocol.WHOIS.value: "WHOIS",
    Protocol.OTHER.value: "Other",
}


def coerce_protocol(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in PROTOCOL_LABELS else Protocol.OTHER.value


class TemplateOrigin(StrEnum):
    OFFICIAL = "official"
    CUSTOM = "custom"


TEMPLATE_ORIGIN_LABELS: dict[str, str] = {
    TemplateOrigin.OFFICIAL.value: "Project templates",
    TemplateOrigin.CUSTOM.value: "Custom templates",
}


class Surface(StrEnum):
    WEB = "web"
    SERVICES = "services"
    FULL = "full"


SURFACE_LABELS: dict[str, str] = {
    Surface.WEB.value: "Web assets",
    Surface.SERVICES.value: "Web assets and network services",
    Surface.FULL.value: "Everything, including hostnames",
}


class CoverageStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


COVERAGE_STATUS_LABELS: dict[str, str] = {
    CoverageStatus.COMPLETED.value: "Completed",
    CoverageStatus.PARTIAL.value: "Partial",
    CoverageStatus.FAILED.value: "Failed",
    CoverageStatus.SKIPPED.value: "Not run",
}


@dataclass(frozen=True)
class TemplateSet:
    key: str
    label: str
    description: str
    tags: tuple[str, ...] = ()
    dirs: tuple[str, ...] = ()
    default: bool = False
    headless: bool = False


# curated bundles over the template library; a set is a tag or directory filter, never a copy
TEMPLATE_SETS: tuple[TemplateSet, ...] = (
    TemplateSet(
        key="kev",
        label="Known exploited",
        description="Weaknesses with confirmed exploitation in the wild.",
        tags=("kev",),
        default=True,
    ),
    TemplateSet(
        key="cve",
        label="Published CVEs",
        description="Checks tied to a published vulnerability identifier.",
        tags=("cve",),
        default=True,
    ),
    TemplateSet(
        key="panel",
        label="Exposed panels",
        description="Administrative and management interfaces reachable without a gateway.",
        tags=("panel", "login"),
        default=True,
    ),
    TemplateSet(
        key="exposure",
        label="Exposed data",
        description="Source, backups, credentials and configuration served to the internet.",
        tags=("exposure", "files", "config", "backup", "disclosure"),
        dirs=("http/exposures",),
        default=True,
    ),
    TemplateSet(
        key="misconfiguration",
        label="Misconfiguration",
        description="Services left in a state their operator did not intend.",
        tags=("misconfig", "unauth", "auth-bypass"),
        default=True,
    ),
    TemplateSet(
        key="default-login",
        label="Default credentials",
        description="Accounts still on the credentials they shipped with.",
        tags=("default-login",),
        default=True,
    ),
    TemplateSet(
        key="takeover",
        label="Subdomain takeover",
        description="Names pointing at infrastructure that can be claimed by someone else.",
        tags=("takeover",),
        default=True,
    ),
    TemplateSet(
        key="injection",
        label="Injection",
        description="Untrusted input reaching an interpreter: SQL, template, command or path.",
        tags=(
            "sqli",
            "xss",
            "ssti",
            "rce",
            "lfi",
            "ssrf",
            "xxe",
            "injection",
            "traversal",
        ),
    ),
    TemplateSet(
        key="cloud",
        label="Cloud storage",
        description="Buckets, blobs and cloud metadata reachable from outside the account.",
        tags=("aws", "azure", "gcp", "s3", "bucket", "storage"),
        dirs=("cloud",),
    ),
    TemplateSet(
        key="network",
        label="Network services",
        description="Checks that speak a protocol other than HTTP.",
        dirs=("network",),
    ),
    TemplateSet(
        key="ssl",
        label="TLS and certificates",
        description="Transport security defects on the certificate or the negotiation.",
        dirs=("ssl",),
    ),
    TemplateSet(
        key="dns",
        label="DNS hygiene",
        description="Record-level defects: dangling names, zone transfer, mail policy.",
        dirs=("dns",),
    ),
    TemplateSet(
        key="headless",
        label="Browser checks",
        description="Checks that need a rendered page. Slower, and only run with a browser enabled.",
        dirs=("headless",),
        headless=True,
    ),
    TemplateSet(
        key="technology",
        label="Technology detection",
        description="Identifies software rather than reporting a weakness. High volume, all informational.",
        tags=("tech", "detect", "fingerprint"),
    ),
)

TEMPLATE_SET_KEYS: tuple[str, ...] = tuple(s.key for s in TEMPLATE_SETS)
TEMPLATE_SET_BY_KEY: dict[str, TemplateSet] = {s.key: s for s in TEMPLATE_SETS}
DEFAULT_TEMPLATE_SETS: list[str] = [s.key for s in TEMPLATE_SETS if s.default]
HEADLESS_SETS: frozenset[str] = frozenset(s.key for s in TEMPLATE_SETS if s.headless)


def reject_unknown(values: list[str], known, axis: str) -> list[str]:
    """A plan's count is a promise, so a value the library cannot honour is refused here."""
    unknown = [v for v in values if v not in known]
    if unknown:
        msg = f"Unknown {axis}: {', '.join(sorted(unknown))}. Choose from: {', '.join(known)}."
        raise ValueError(msg)
    return values


# nuclei's code protocol runs shell on the scanner host; an uploaded template may never use it
FORBIDDEN_TEMPLATE_KEYS: frozenset[str] = frozenset({"code"})

KEV_TAG = "kev"
CVE_TAG = "cve"

EPSS_HIGH = 0.5
CVSS_HIGH = 7.0


def is_kev(tags: list[str] | tuple[str, ...] | None) -> bool:
    return KEV_TAG in {t.lower() for t in tags or ()}


@dataclass(frozen=True)
class RiskSignal:
    key: str
    label: str
    description: str


# the reasons a finding outranks another finding of the same severity
RISK_SIGNALS: tuple[RiskSignal, ...] = (
    RiskSignal("kev", "Known exploited", "Listed as exploited in the wild."),
    RiskSignal(
        "epss", "Likely to be exploited", f"EPSS above {int(EPSS_HIGH * 100)}%."
    ),
    RiskSignal("new", "New", "Not present at the previous scan of this target."),
    RiskSignal(
        "origin", "Origin exposed", "On an address that also answers behind the CDN."
    ),
)
