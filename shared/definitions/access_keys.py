"""Access keys: levels, expiry choices and what a key may call."""

from __future__ import annotations

from enum import StrEnum

ACCESS_KEY_PREFIX = "rngkey_"
MAX_ACCESS_KEYS = 20
MAX_NAME_LENGTH = 80


class AccessKeyLevel(StrEnum):
    READ = "read"
    WRITE = "write"


LEVEL_LABELS: dict[AccessKeyLevel, str] = {
    AccessKeyLevel.READ: "Read",
    AccessKeyLevel.WRITE: "Read and write",
}

LEVEL_HELP: dict[AccessKeyLevel, str] = {
    AccessKeyLevel.READ: "Search, list, export and compare.",
    AccessKeyLevel.WRITE: "Also targets, scans, triage and notes.",
}

# days; None is no expiry
EXPIRY_DAYS: tuple[int | None, ...] = (30, 90, 365, None)
DEFAULT_EXPIRY_DAYS = 90

EXPIRY_LABELS: dict[int | None, str] = {
    30: "30 days",
    90: "90 days",
    365: "1 year",
    None: "No expiry",
}

_CHOICES = list(EXPIRY_LABELS.values())
EXPIRY_DETAIL = f"Choose an expiry: {', '.join(_CHOICES[:-1])} or {_CHOICES[-1]}."


class KeyRule(StrEnum):
    REFUSED = "refused"
    READ = "read"
    WRITE = "write"


REFUSED_DETAIL = "Access keys cannot call this endpoint."
READ_ONLY_DETAIL = "Access key is read-only."
INVALID_DETAIL = "Access key is invalid, expired or revoked."
LIMIT_DETAIL = f"An account holds at most {MAX_ACCESS_KEYS} access keys."

# ---------- limits and bookkeeping ----------

FAILURE_KEY = "auth:key-from:{address}"
FAILURE_LIMIT = 50
FAILURE_WINDOW_SECONDS = 900
LAST_USE_SECONDS = 60
USED_KEY = "access-key:used:{key_id}"
CALLS_KEY = "access-key:calls:{key_id}"
OWNER_KEY = "access-key:owner:{token_hash}"
OWNER_SECONDS = 300

# ---------- classification ----------

# paths relative to the api prefix, matched on whole segments
REFUSED_PREFIXES: tuple[str, ...] = (
    "/auth",
    "/access-keys",
    "/api-keys",
    "/mcp",
    "/connectors",
    "/remote-control",
    "/ask",
    "/investigate",
    "/events",
)
# exact templates; AI-spending routes
REFUSED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/interest/scan/{scan_id}/judge"),
        ("POST", "/interest/scan/{scan_id}/suggestions"),
        ("POST", "/reports"),
        ("POST", "/reports/{report_id}/retry"),
    }
)
ALLOWED_UNDER_REFUSED: frozenset[tuple[str, str]] = frozenset({("GET", "/auth/me")})

READ_METHODS = frozenset({"GET", "HEAD"})

# GET routes that spend a provider quota
WRITING_GETS: frozenset[str] = frozenset(
    {
        "/tools/viewdns/reverse-ip/{host}",
        "/tools/viewdns/reverse-ns/{nameserver}",
        "/tools/viewdns/reverse-whois",
    }
)

READING_POSTS: frozenset[str] = frozenset(
    {
        *(
            f"/{dimension}/search{tail}"
            for dimension in (
                "subdomains",
                "ips",
                "ports",
                "endpoints",
                "vulnerabilities",
            )
            for tail in ("", "/counts", "/groups", "/leads", "/tabs")
        ),
        "/subdomains/search/renders",
        "/vulnerabilities/search/issues",
        "/secrets/search",
        "/secrets/search/counts",
        "/secrets/search/groups",
        "/software/search",
        "/software/search/counts",
        "/vuln-templates/search",
        "/subdomains/timeline",
        "/subdomains/timeline/renders",
        "/ports/timeline",
        "/vulnerabilities/timeline",
        "/endpoints/tree",
        "/endpoints/tree/hosts",
        "/endpoints/tree/leaves",
        "/endpoints/gone",
        "/targets/{target_id}/assets",
        "/tools/viewdns/cached-counts",
        "/exports",
        "/interest/project",
        "/interest/scan/{scan_id}",
    }
)


def _under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def refused(method: str, path: str) -> bool:
    if (method, path) in ALLOWED_UNDER_REFUSED:
        return False
    return (method, path) in REFUSED_ROUTES or any(
        _under(path, p) for p in REFUSED_PREFIXES
    )


def key_rule(method: str, path: str, *, gated: bool) -> KeyRule:
    """What an access key needs to call a route; gated is an administrator or stream route."""
    method = method.upper()
    if gated or refused(method, path):
        return KeyRule.REFUSED
    if method in READ_METHODS and path not in WRITING_GETS:
        return KeyRule.READ
    if method == "POST" and path in READING_POSTS:
        return KeyRule.READ
    return KeyRule.WRITE


def allows(level: AccessKeyLevel, rule: KeyRule) -> bool:
    if rule is KeyRule.REFUSED:
        return False
    return rule is KeyRule.READ or level is AccessKeyLevel.WRITE
