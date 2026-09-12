"""The vocabulary of a scan-to-scan comparison: verbs, watched fields and named signals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.surface import SurfaceDimension


class ChangeVerb(StrEnum):
    APPEARED = "appeared"
    CHANGED = "changed"
    DISAPPEARED = "disappeared"
    UNCONFIRMED = "unconfirmed"
    UNCHANGED = "unchanged"


VERB_ORDER: tuple[str, ...] = (
    ChangeVerb.APPEARED.value,
    ChangeVerb.CHANGED.value,
    ChangeVerb.DISAPPEARED.value,
    ChangeVerb.UNCONFIRMED.value,
    ChangeVerb.UNCHANGED.value,
)

LISTED_VERBS: tuple[str, ...] = VERB_ORDER[:-1]


class Comparability(StrEnum):
    LIKE_FOR_LIKE = "like_for_like"
    SETTINGS_DIFFER = "settings_differ"
    QUALITY_DIFFERS = "quality_differs"
    NOT_COVERED = "not_covered"


class FieldKind(StrEnum):
    SCALAR = "scalar"
    LIST = "list"
    BOOL = "bool"
    DATE = "date"
    OPAQUE = "opaque"


class Tone(StrEnum):
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class WatchedField:
    name: str
    label: str
    kind: str = FieldKind.SCALAR.value


# ---------- watched fields ----------

_HOST_FIELDS: tuple[WatchedField, ...] = (
    WatchedField("http_status", "Status"),
    WatchedField("final_url", "Final URL"),
    WatchedField("page_title", "Title"),
    WatchedField("webserver", "Server"),
    WatchedField("waf", "WAF"),
    WatchedField("cdn_name", "CDN"),
    WatchedField("cname", "CNAME"),
    WatchedField("favicon_hash", "Favicon", FieldKind.OPAQUE.value),
    WatchedField("is_active", "Responding", FieldKind.BOOL.value),
    WatchedField("tls_expired", "Certificate expired", FieldKind.BOOL.value),
    WatchedField("tls_self_signed", "Self-signed", FieldKind.BOOL.value),
    WatchedField("tls_not_after", "Certificate expiry", FieldKind.DATE.value),
    WatchedField("tech", "Technology", FieldKind.LIST.value),
    WatchedField("resolved_ips", "Addresses", FieldKind.LIST.value),
)

_ENDPOINT_FIELDS: tuple[WatchedField, ...] = (
    WatchedField("status_code", "Status"),
    WatchedField("content_hash", "Body", FieldKind.OPAQUE.value),
    WatchedField("content_type", "Content type"),
    WatchedField("redirect_location", "Redirects to"),
    WatchedField("param_count", "Parameters"),
    WatchedField("is_probed", "Probed", FieldKind.BOOL.value),
    WatchedField("tech", "Technology", FieldKind.LIST.value),
    WatchedField("interest", "Interest", FieldKind.LIST.value),
)

_SERVICE_FIELDS: tuple[WatchedField, ...] = (
    WatchedField("state", "State"),
    WatchedField("service_name", "Service"),
    WatchedField("service_class", "Class"),
    WatchedField("product", "Product"),
    WatchedField("version", "Version"),
    WatchedField("banner", "Banner", FieldKind.OPAQUE.value),
    WatchedField("is_http", "HTTP", FieldKind.BOOL.value),
    WatchedField("tls", "TLS", FieldKind.BOOL.value),
    WatchedField("cpe", "CPE", FieldKind.LIST.value),
)

_ADDRESS_FIELDS: tuple[WatchedField, ...] = (
    WatchedField("asn", "ASN"),
    WatchedField("asn_org", "Network"),
    WatchedField("prefix", "Prefix"),
    WatchedField("country", "Country"),
    WatchedField("cdn_name", "CDN"),
    WatchedField("is_cdn", "Behind CDN", FieldKind.BOOL.value),
    WatchedField("is_alive", "Responding", FieldKind.BOOL.value),
    WatchedField("ptr_hostnames", "PTR", FieldKind.LIST.value),
)

_VULN_FIELDS: tuple[WatchedField, ...] = (
    WatchedField("severity", "Severity"),
    WatchedField("template_available", "Template available", FieldKind.BOOL.value),
    WatchedField("extracted_results", "Extracted", FieldKind.LIST.value),
)

WATCHED_FIELDS: dict[str, tuple[WatchedField, ...]] = {
    SurfaceDimension.WEB_ASSETS.value: _HOST_FIELDS,
    SurfaceDimension.ENDPOINTS.value: _ENDPOINT_FIELDS,
    SurfaceDimension.SERVICES.value: _SERVICE_FIELDS,
    SurfaceDimension.IPS.value: _ADDRESS_FIELDS,
    SurfaceDimension.VULNERABILITIES.value: _VULN_FIELDS,
}

# moves every run
IGNORED_FIELDS: dict[str, tuple[str, ...]] = {
    SurfaceDimension.WEB_ASSETS.value: ("content_length", "response_time"),
    SurfaceDimension.ENDPOINTS.value: (
        "words",
        "lines",
        "response_time",
        "content_length",
        "variants",
    ),
    SurfaceDimension.SERVICES.value: ("source",),
    SurfaceDimension.IPS.value: ("source", "scan_policy_reason"),
    SurfaceDimension.VULNERABILITIES.value: ("description", "remediation"),
}

# Class D: moves without a scan
INTEL_FIELDS: tuple[str, ...] = (
    "is_kev",
    "kev_ransomware",
    "kev_due_date",
    "epss_score",
    "epss_percentile",
    "exploit_score",
    "intel_kinds",
    "poc_count",
)


# ---------- identity ----------

COMPARE_KEYS: dict[str, tuple[str, ...]] = {
    SurfaceDimension.WEB_ASSETS.value: ("name",),
    SurfaceDimension.ENDPOINTS.value: ("signature",),
    SurfaceDimension.SERVICES.value: ("ip", "number", "protocol"),
    SurfaceDimension.IPS.value: ("ip",),
    SurfaceDimension.VULNERABILITIES.value: ("fingerprint",),
}


# ---------- named signals ----------


class ChangeSignal(StrEnum):
    KEV_APPEARED = "kev_appeared"
    CRITICAL_APPEARED = "critical_appeared"
    FINDING_APPEARED = "finding_appeared"
    SEVERITY_RAISED = "severity_raised"
    SENSITIVE_SERVICE_OPENED = "sensitive_service_opened"
    AUTH_DROPPED = "auth_dropped"
    SERVICE_OPENED = "service_opened"
    CERT_EXPIRED = "cert_expired"
    WAF_GONE = "waf_gone"
    CDN_GONE = "cdn_gone"
    HOSTING_MOVED = "hosting_moved"
    HOST_WOKE = "host_woke"
    BODY_CHANGED = "body_changed"
    EXPOSED_HOST_APPEARED = "exposed_host_appeared"
    HOST_APPEARED = "host_appeared"
    ADDRESS_APPEARED = "address_appeared"
    ENDPOINT_APPEARED = "endpoint_appeared"
    ATTRIBUTES_CHANGED = "attributes_changed"
    FINDING_GONE = "finding_gone"
    SERVICE_CLOSED = "service_closed"
    HOST_GONE = "host_gone"
    ASSET_GONE = "asset_gone"


# lower ranks first
SIGNAL_RANK: dict[str, int] = {
    ChangeSignal.KEV_APPEARED.value: 0,
    ChangeSignal.CRITICAL_APPEARED.value: 1,
    ChangeSignal.SENSITIVE_SERVICE_OPENED.value: 2,
    ChangeSignal.AUTH_DROPPED.value: 3,
    ChangeSignal.FINDING_APPEARED.value: 4,
    ChangeSignal.SEVERITY_RAISED.value: 5,
    ChangeSignal.CERT_EXPIRED.value: 6,
    ChangeSignal.WAF_GONE.value: 7,
    ChangeSignal.EXPOSED_HOST_APPEARED.value: 8,
    ChangeSignal.HOSTING_MOVED.value: 9,
    ChangeSignal.HOST_WOKE.value: 10,
    ChangeSignal.CDN_GONE.value: 11,
    ChangeSignal.SERVICE_OPENED.value: 12,
    ChangeSignal.BODY_CHANGED.value: 13,
    ChangeSignal.HOST_APPEARED.value: 14,
    ChangeSignal.ADDRESS_APPEARED.value: 15,
    ChangeSignal.ENDPOINT_APPEARED.value: 16,
    ChangeSignal.ATTRIBUTES_CHANGED.value: 17,
    ChangeSignal.FINDING_GONE.value: 18,
    ChangeSignal.SERVICE_CLOSED.value: 19,
    ChangeSignal.HOST_GONE.value: 20,
    ChangeSignal.ASSET_GONE.value: 21,
}

# ---------- run-level facets ----------


@dataclass(frozen=True)
class RunFacet:
    key: str
    label: str
    path: str
    kind: str = "scalar"
    material: bool = True


class FacetKind(StrEnum):
    SCALAR = "scalar"
    LIST = "list"
    BOOL = "bool"
    COUNT = "count"
    MASKED = "masked"


RUN_FACETS: tuple[RunFacet, ...] = (
    RunFacet("auth", "Authentication", "_auth.auth_type"),
    RunFacet("headers", "Extra headers", "headers", FacetKind.COUNT.value),
    RunFacet("intensity", "Intensity", "intensity"),
    RunFacet("proxy", "Proxy", "proxy_url", FacetKind.MASKED.value),
    RunFacet("http_protocol", "HTTP protocol", "http_protocol"),
    RunFacet("crawl", "Crawl responses", "global_http_crawl", FacetKind.BOOL.value),
    RunFacet(
        "excluded_subdomains",
        "Excluded hosts",
        "excluded_subdomains",
        FacetKind.LIST.value,
    ),
    RunFacet(
        "excluded_paths", "Excluded paths", "excluded_paths", FacetKind.LIST.value
    ),
    RunFacet(
        "excluded_ips", "Excluded addresses", "excluded_ips", FacetKind.LIST.value
    ),
    RunFacet(
        "included_subdomains",
        "Only these hosts",
        "included_subdomains",
        FacetKind.LIST.value,
    ),
    RunFacet(
        "rate_ceiling",
        "Global rate limit",
        "global_rate_limit_ceiling",
        material=False,
    ),
    RunFacet("threads", "Threads", "global_threads", material=False),
    RunFacet(
        "thread_multiplier", "Thread multiplier", "thread_multiplier", material=False
    ),
    RunFacet(
        "timeout_multiplier", "Timeout multiplier", "timeout_multiplier", material=False
    ),
)


# ---------- why a pair cannot be compared ----------


class Refusal(StrEnum):
    DIFFERENT_TARGET = "different_target"
    UNFINISHED = "unfinished"
    FOCUSED_AGAINST_FULL = "focused_against_full"
    FULL_AGAINST_FOCUSED = "full_against_focused"
    SAME_RUN = "same_run"
    NO_EARLIER_RUN = "no_earlier_run"
    NEED_ONE_MORE = "need_one_more"
    TOO_MANY = "too_many"


REFUSAL_REASON: dict[str, str] = {
    Refusal.DIFFERENT_TARGET.value: "Both runs must cover the same target.",
    Refusal.UNFINISHED.value: "This run has not finished.",
    Refusal.FOCUSED_AGAINST_FULL.value: (
        "A focused run covers only the assets it was seeded with. "
        "Open it to see its recheck against its parent run."
    ),
    Refusal.FULL_AGAINST_FOCUSED.value: (
        "A focused run covers only the assets it was seeded with. "
        "Compare two full runs instead."
    ),
    Refusal.SAME_RUN.value: "Pick two different runs.",
    Refusal.NO_EARLIER_RUN.value: "No earlier run of this target to compare with.",
    Refusal.NEED_ONE_MORE.value: "Select one more run of the same target.",
    Refusal.TOO_MANY.value: "Select exactly two runs.",
}

MAX_RUN_DIFFERENCES = 12


# ---------- unified diff ----------

DIFF_MARK: dict[str, str] = {
    ChangeVerb.APPEARED.value: "+",
    ChangeVerb.CHANGED.value: "~",
    ChangeVerb.DISAPPEARED.value: "-",
    ChangeVerb.UNCONFIRMED.value: "?",
    ChangeVerb.UNCHANGED.value: " ",
}

MAX_DIFF_LINES = 5000
DIFF_PAGE = 200
DIFF_FIELD_INDENT = "    "

DEFAULT_RANK = 99

AUTH_STATUS: tuple[int, ...] = (401, 403)
OK_MIN = 200
OK_MAX = 400
MAX_ROWS_PER_PAGE = 100
DEFAULT_ROWS_PER_PAGE = 50
MAX_COMPARABLE_RUNS = 40
