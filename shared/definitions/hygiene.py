"""Hardening checks read from stored HTTP responses."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.interest import TONE_INFO, TONE_WARNING

HSTS_MIN_MAX_AGE = 31_536_000
MAX_EVIDENCE = 200
BACKFILL_SCANS_PER_TICK = 25
BACKFILL_BATCH = 2_000


class HygieneCheck(StrEnum):
    NO_HSTS = "no_hsts"
    HSTS_SHORT = "hsts_short"
    NO_HTTPS_REDIRECT = "no_https_redirect"
    NO_FRAME_PROTECTION = "no_frame_protection"
    NO_NOSNIFF = "no_nosniff"
    NO_CSP = "no_csp"
    CSP_REPORT_ONLY = "csp_report_only"
    CSP_UNSAFE_INLINE = "csp_unsafe_inline"
    CSP_WILDCARD_SCRIPT = "csp_wildcard_script"
    COOKIE_NO_SECURE = "cookie_no_secure"
    COOKIE_NO_HTTPONLY = "cookie_no_httponly"
    CACHEABLE_SESSION = "cacheable_session"
    CORS_CREDENTIALS = "cors_credentials"
    CORS_ANY_ORIGIN = "cors_any_origin"
    SERVER_VERSION = "server_version"
    RUNTIME_DISCLOSED = "runtime_disclosed"
    NO_REFERRER_POLICY = "no_referrer_policy"


class HygieneGroup(StrEnum):
    TRANSPORT = "transport"
    CONTENT = "content"
    COOKIES = "cookies"
    CROSS_ORIGIN = "cross_origin"
    DISCLOSURE = "disclosure"


GROUP_LABELS: dict[str, str] = {
    HygieneGroup.TRANSPORT.value: "Transport",
    HygieneGroup.CONTENT.value: "Content",
    HygieneGroup.COOKIES.value: "Cookies",
    HygieneGroup.CROSS_ORIGIN.value: "Cross-origin",
    HygieneGroup.DISCLOSURE.value: "Disclosure",
}

# grammar-only values
ANY = "any"
NONE = "none"
TONES: tuple[str, ...] = (TONE_WARNING, TONE_INFO)


@dataclass(frozen=True)
class CheckSpec:
    key: str
    label: str
    control: str
    help: str
    applies: str
    fix: str
    header: str
    group: str
    tone: str

    @property
    def query(self) -> str:
        return f"hygiene:{self.key}"


CHECKS: tuple[CheckSpec, ...] = (
    CheckSpec(
        HygieneCheck.NO_HTTPS_REDIRECT.value,
        "Plaintext without redirect",
        "HTTPS redirect",
        "An http response that does not redirect to https.",
        "Every http response.",
        "Answer http with a 301 to the https URL.",
        "Location",
        HygieneGroup.TRANSPORT.value,
        TONE_WARNING,
    ),
    CheckSpec(
        HygieneCheck.COOKIE_NO_SECURE.value,
        "Cookie without Secure",
        "Cookie Secure",
        "A cookie set over https without the Secure attribute.",
        "Every https response that sets a cookie.",
        "Add Secure to every Set-Cookie on https.",
        "Set-Cookie",
        HygieneGroup.COOKIES.value,
        TONE_WARNING,
    ),
    CheckSpec(
        HygieneCheck.COOKIE_NO_HTTPONLY.value,
        "Session cookie without HttpOnly",
        "Cookie HttpOnly",
        "A session or authentication cookie without the HttpOnly attribute.",
        "Every response that sets a session-named cookie.",
        "Add HttpOnly to session and authentication cookies.",
        "Set-Cookie",
        HygieneGroup.COOKIES.value,
        TONE_WARNING,
    ),
    CheckSpec(
        HygieneCheck.CACHEABLE_SESSION.value,
        "Session cookie in a cacheable response",
        "Session cache control",
        "A response that sets a session cookie without Cache-Control: no-store or private.",
        "Every response that sets a session-named cookie.",
        "Send Cache-Control: no-store on responses that set session cookies.",
        "Cache-Control",
        HygieneGroup.COOKIES.value,
        TONE_WARNING,
    ),
    CheckSpec(
        HygieneCheck.CORS_CREDENTIALS.value,
        "CORS credentials with wildcard origin",
        "CORS credentials",
        "Access-Control-Allow-Origin is * or null while Access-Control-Allow-Credentials is true.",
        "Every response with Access-Control-Allow-Origin.",
        "Name the allowed origin exactly, or drop Access-Control-Allow-Credentials.",
        "Access-Control-Allow-Origin",
        HygieneGroup.CROSS_ORIGIN.value,
        TONE_WARNING,
    ),
    CheckSpec(
        HygieneCheck.NO_FRAME_PROTECTION.value,
        "No framing protection",
        "Framing protection",
        "An HTML page without X-Frame-Options or a CSP frame-ancestors directive.",
        "Every 2xx HTML response.",
        "Send Content-Security-Policy: frame-ancestors 'self' or X-Frame-Options: DENY.",
        "X-Frame-Options",
        HygieneGroup.CONTENT.value,
        TONE_WARNING,
    ),
    CheckSpec(
        HygieneCheck.CSP_UNSAFE_INLINE.value,
        "CSP allows inline scripts",
        "CSP inline scripts",
        "script-src permits 'unsafe-inline' with no nonce, hash or 'strict-dynamic'.",
        "Every response with an enforcing Content-Security-Policy that governs scripts.",
        "Replace 'unsafe-inline' with nonces or hashes.",
        "Content-Security-Policy",
        HygieneGroup.CONTENT.value,
        TONE_WARNING,
    ),
    CheckSpec(
        HygieneCheck.CSP_WILDCARD_SCRIPT.value,
        "CSP allows any script origin",
        "CSP script origins",
        "script-src includes *, https:, http: or data:.",
        "Every response with an enforcing Content-Security-Policy that governs scripts.",
        "List the script origins the page uses.",
        "Content-Security-Policy",
        HygieneGroup.CONTENT.value,
        TONE_WARNING,
    ),
    CheckSpec(
        HygieneCheck.NO_HSTS.value,
        "No HSTS",
        "HSTS",
        "An https response without Strict-Transport-Security.",
        "Every https response.",
        "Send Strict-Transport-Security: max-age=31536000; includeSubDomains.",
        "Strict-Transport-Security",
        HygieneGroup.TRANSPORT.value,
        TONE_INFO,
    ),
    CheckSpec(
        HygieneCheck.HSTS_SHORT.value,
        "HSTS under a year",
        "HSTS max-age",
        "Strict-Transport-Security max-age below 31536000 seconds.",
        "Every response with Strict-Transport-Security.",
        "Raise max-age to 31536000 or more.",
        "Strict-Transport-Security",
        HygieneGroup.TRANSPORT.value,
        TONE_INFO,
    ),
    CheckSpec(
        HygieneCheck.NO_CSP.value,
        "No Content-Security-Policy",
        "Content-Security-Policy",
        "An HTML page without a Content-Security-Policy header.",
        "Every 2xx HTML response.",
        "Send a Content-Security-Policy header.",
        "Content-Security-Policy",
        HygieneGroup.CONTENT.value,
        TONE_INFO,
    ),
    CheckSpec(
        HygieneCheck.CSP_REPORT_ONLY.value,
        "CSP report-only",
        "Enforcing CSP",
        "Content-Security-Policy-Report-Only without an enforcing policy.",
        "Every 2xx HTML response.",
        "Promote the report-only policy to Content-Security-Policy.",
        "Content-Security-Policy-Report-Only",
        HygieneGroup.CONTENT.value,
        TONE_INFO,
    ),
    CheckSpec(
        HygieneCheck.NO_NOSNIFF.value,
        "No nosniff",
        "nosniff",
        "X-Content-Type-Options: nosniff is absent.",
        "Every 2xx response with a content type.",
        "Send X-Content-Type-Options: nosniff.",
        "X-Content-Type-Options",
        HygieneGroup.CONTENT.value,
        TONE_INFO,
    ),
    CheckSpec(
        HygieneCheck.NO_REFERRER_POLICY.value,
        "No Referrer-Policy",
        "Referrer-Policy",
        "An HTML page without a Referrer-Policy header.",
        "Every 2xx HTML response.",
        "Send Referrer-Policy: strict-origin-when-cross-origin.",
        "Referrer-Policy",
        HygieneGroup.CONTENT.value,
        TONE_INFO,
    ),
    CheckSpec(
        HygieneCheck.CORS_ANY_ORIGIN.value,
        "CORS allows any origin",
        "CORS origin",
        "Access-Control-Allow-Origin: *.",
        "Every response with Access-Control-Allow-Origin.",
        "Name the allowed origins if the resource is not public.",
        "Access-Control-Allow-Origin",
        HygieneGroup.CROSS_ORIGIN.value,
        TONE_INFO,
    ),
    CheckSpec(
        HygieneCheck.SERVER_VERSION.value,
        "Server version disclosed",
        "Server banner",
        "The Server header carries a version number.",
        "Every response with a Server header.",
        "Strip the version from the Server header.",
        "Server",
        HygieneGroup.DISCLOSURE.value,
        TONE_INFO,
    ),
    CheckSpec(
        HygieneCheck.RUNTIME_DISCLOSED.value,
        "Runtime disclosed",
        "Runtime headers",
        "X-Powered-By, X-AspNet-Version or X-Generator names the platform.",
        "Every response.",
        "Remove X-Powered-By and related headers.",
        "X-Powered-By",
        HygieneGroup.DISCLOSURE.value,
        TONE_INFO,
    ),
)

CHECK_BY_KEY: dict[str, CheckSpec] = {c.key: c for c in CHECKS}
CHECK_KEYS: tuple[str, ...] = tuple(c.key for c in CHECKS)
CHECK_ORDER: dict[str, int] = {c.key: i for i, c in enumerate(CHECKS)}
WARNING_KEYS: tuple[str, ...] = tuple(c.key for c in CHECKS if c.tone == TONE_WARNING)
INFO_KEYS: tuple[str, ...] = tuple(c.key for c in CHECKS if c.tone == TONE_INFO)
KEYS_BY_TONE: dict[str, tuple[str, ...]] = {
    TONE_WARNING: WARNING_KEYS,
    TONE_INFO: INFO_KEYS,
}
QUERY_VALUES: tuple[str, ...] = (*CHECK_KEYS, *TONES, ANY, NONE)
