"""What makes an asset worth a look, and how much each reason weighs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_SCORE = 100
MAX_SIGNALS_PER_HOST = 8
MAX_RULES = 200
MAX_KEYWORDS = 120
MAX_RULE_NAME = 80
MAX_REASON = 400
MAX_EVIDENCE = 300

# a correlation signal is only meaningful once the estate is big enough to have a norm
MIN_ESTATE_FOR_RARITY = 25
RARE_SHARE = 0.05
RARE_MAX_HOSTS = 3
EDGE_MAJORITY = 0.7


class InterestSource(StrEnum):
    KEYWORD = "keyword"
    RULE = "rule"
    CORRELATION = "correlation"
    AI = "ai"


SOURCE_LABELS: dict[str, str] = {
    InterestSource.KEYWORD.value: "Your keywords",
    InterestSource.RULE.value: "Rule",
    InterestSource.CORRELATION.value: "Correlation",
    InterestSource.AI.value: "AI",
}

SOURCE_HELP: dict[str, str] = {
    InterestSource.KEYWORD.value: "Matched a keyword you added.",
    InterestSource.RULE.value: "Matched a saved query.",
    InterestSource.CORRELATION.value: "Stands out from the rest of this estate.",
    InterestSource.AI.value: "A judgement written by a model, not an observation.",
}

# a judgement is never presented as a fact; the UI must always name its source
JUDGEMENT_SOURCES: frozenset[str] = frozenset({InterestSource.AI.value})


class InterestKind(StrEnum):
    ADMIN_INTERFACE = "admin_interface"
    DEVELOPER_TOOLING = "developer_tooling"
    REMOTE_ACCESS = "remote_access"
    BUSINESS_SYSTEM = "business_system"
    NON_PRODUCTION = "non_production"
    LEGACY = "legacy"
    INTERNAL_NAMING = "internal_naming"
    NO_AUTHENTICATION = "no_authentication"
    EXPOSED_CONTENT = "exposed_content"
    DIAGNOSTIC = "diagnostic"
    SENSITIVE_SERVICE = "sensitive_service"
    CERTIFICATE_ANOMALY = "certificate_anomaly"
    TAKEOVER_RISK = "takeover_risk"
    NETWORK_OUTLIER = "network_outlier"
    RARE_TECHNOLOGY = "rare_technology"
    RARE_IDENTITY = "rare_identity"
    UNPROTECTED_EDGE = "unprotected_edge"
    NEWLY_APPEARED = "newly_appeared"
    OTHER = "other"


@dataclass(frozen=True)
class KindSpec:
    key: str
    label: str
    help: str
    weight: int
    tone: str


TONE_WARNING = "warning"
TONE_INFO = "info"
TONE_NEUTRAL = "neutral"

KINDS: tuple[KindSpec, ...] = (
    KindSpec(
        InterestKind.ADMIN_INTERFACE.value,
        "Administrative interface",
        "A control panel or management console reachable from the internet.",
        30,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.DEVELOPER_TOOLING.value,
        "Developer tooling",
        "Build, source or observability tooling answering on a public hostname.",
        28,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.REMOTE_ACCESS.value,
        "Remote access",
        "A VPN, gateway or remote desktop portal, routinely targeted.",
        28,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.BUSINESS_SYSTEM.value,
        "Business system",
        "An ERP, finance or HR application exposed to the internet.",
        24,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.NON_PRODUCTION.value,
        "Non-production",
        "Named as a staging, test or sandbox deployment.",
        20,
        TONE_INFO,
    ),
    KindSpec(
        InterestKind.LEGACY.value,
        "Legacy",
        "Named as old, retired or superseded, and still answering.",
        22,
        TONE_INFO,
    ),
    KindSpec(
        InterestKind.INTERNAL_NAMING.value,
        "Internal naming",
        "Carries internal or private naming on a publicly resolvable host.",
        18,
        TONE_INFO,
    ),
    KindSpec(
        InterestKind.NO_AUTHENTICATION.value,
        "No authentication",
        "Answered without a login wall where one would be expected.",
        26,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.EXPOSED_CONTENT.value,
        "Exposed content",
        "Serves a directory listing, an archive or a file that should not be public.",
        30,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.DIAGNOSTIC.value,
        "Diagnostic output",
        "Returns stack traces, debug pages or environment detail.",
        26,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.SENSITIVE_SERVICE.value,
        "Sensitive service",
        "An administrative or database port is open on this host.",
        26,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.CERTIFICATE_ANOMALY.value,
        "Certificate anomaly",
        "The certificate is expired, self-signed or names something unexpected.",
        14,
        TONE_INFO,
    ),
    KindSpec(
        InterestKind.TAKEOVER_RISK.value,
        "Takeover risk",
        "An alias points somewhere that no longer answers.",
        30,
        TONE_WARNING,
    ),
    KindSpec(
        InterestKind.NETWORK_OUTLIER.value,
        "Network outlier",
        "Sits on a network almost nothing else in this estate uses.",
        18,
        TONE_INFO,
    ),
    KindSpec(
        InterestKind.RARE_TECHNOLOGY.value,
        "Rare technology",
        "Runs software almost nothing else in this estate runs.",
        16,
        TONE_INFO,
    ),
    KindSpec(
        InterestKind.RARE_IDENTITY.value,
        "Distinct application",
        "Serves an icon or page shared by almost nothing else here, so it is its own application.",
        14,
        TONE_INFO,
    ),
    KindSpec(
        InterestKind.UNPROTECTED_EDGE.value,
        "Outside the edge",
        "Answers directly while the rest of this estate sits behind a CDN.",
        20,
        TONE_INFO,
    ),
    KindSpec(
        InterestKind.NEWLY_APPEARED.value,
        "New",
        "Absent from the previous scan of this target.",
        10,
        TONE_NEUTRAL,
    ),
    KindSpec(
        InterestKind.OTHER.value,
        "Worth a look",
        "Flagged without a more specific reason.",
        12,
        TONE_NEUTRAL,
    ),
)

KIND_BY_KEY: dict[str, KindSpec] = {k.key: k for k in KINDS}
KIND_KEYS: tuple[str, ...] = tuple(k.key for k in KINDS)
KIND_LABELS: dict[str, str] = {k.key: k.label for k in KINDS}
KIND_HELP: dict[str, str] = {k.key: k.help for k in KINDS}
KIND_WEIGHTS: dict[str, int] = {k.key: k.weight for k in KINDS}
KIND_TONES: dict[str, str] = {k.key: k.tone for k in KINDS}


def kind_weight(kind: str) -> int:
    spec = KIND_BY_KEY.get(kind)
    return spec.weight if spec else KIND_BY_KEY[InterestKind.OTHER.value].weight


def kind_label(kind: str) -> str:
    spec = KIND_BY_KEY.get(kind)
    return spec.label if spec else kind.replace("_", " ").capitalize()


def coerce_kind(value: str | None) -> str:
    raw = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return raw if raw in KIND_BY_KEY else InterestKind.OTHER.value


class InterestBand(StrEnum):
    NOTABLE = "notable"
    HIGH = "high"
    CRITICAL = "critical"


BAND_ORDER: tuple[str, ...] = (
    InterestBand.CRITICAL.value,
    InterestBand.HIGH.value,
    InterestBand.NOTABLE.value,
)

BAND_LABELS: dict[str, str] = {
    InterestBand.CRITICAL.value: "Look first",
    InterestBand.HIGH.value: "Worth a look",
    InterestBand.NOTABLE.value: "Notable",
}

BAND_TONES: dict[str, str] = {
    InterestBand.CRITICAL.value: "destructive",
    InterestBand.HIGH.value: TONE_WARNING,
    InterestBand.NOTABLE.value: TONE_INFO,
}

# score at or above which a host enters the band
BAND_FLOOR: dict[str, int] = {
    InterestBand.CRITICAL.value: 55,
    InterestBand.HIGH.value: 30,
    InterestBand.NOTABLE.value: 1,
}


def band_for(score: int) -> str:
    for band in BAND_ORDER:
        if score >= BAND_FLOOR[band]:
            return band
    return InterestBand.NOTABLE.value


DEFAULT_NOTIFY_BAND = InterestBand.HIGH.value


class RuleMode(StrEnum):
    KEYWORD = "keyword"
    QUERY = "query"


RULE_MODE_LABELS: dict[str, str] = {
    RuleMode.KEYWORD.value: "Keywords",
    RuleMode.QUERY.value: "Query",
}

KEYWORD_FIELDS: tuple[str, ...] = ("host", "title")
KEYWORD_FIELD_LABELS: dict[str, str] = {
    "host": "Hostname",
    "title": "Page title",
}
