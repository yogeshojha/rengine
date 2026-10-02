"""Identity kinds two hosts can share, and the thresholds that make a shared identity significant."""

from __future__ import annotations

from enum import StrEnum

MAX_GRAPH_HOSTS = 3000
MAX_HUBS_PER_KIND = 80
MIN_SHARED = 2
# a body this small is not an identity
MIN_BODY_BYTES = 512
# two renders within this many bits of each other are the same page
SCREENSHOT_DISTANCE = 2
# a render whose hash sets fewer bits than this is blank, not an identity
SCREENSHOT_MIN_POPCOUNT = 4
# hidden by default at or above this share
COMMON_SHARE = 0.5
MIN_ESTATE_FOR_COMMON = 25


class CorrelationKind(StrEnum):
    IP = "ip"
    CNAME = "cname"
    TITLE = "title"
    FAVICON = "favicon"
    BODY = "content_hash"
    SCREENSHOT = "screenshot"
    JARM = "jarm"
    CERT = "cert.fingerprint"
    CERT_ISSUER = "cert.issuer"
    HEADERS = "header_hash"
    TECH = "tech"
    SERVER = "server"
    CDN = "cdn"
    ASN = "asn"
    TRACKING = "tracking"


CORRELATION_KIND_LABELS: dict[str, str] = {
    CorrelationKind.IP.value: "Address",
    CorrelationKind.CNAME.value: "CNAME target",
    CorrelationKind.TITLE.value: "Page title",
    CorrelationKind.FAVICON.value: "Favicon",
    CorrelationKind.BODY.value: "Body hash",
    CorrelationKind.SCREENSHOT.value: "Rendered page",
    CorrelationKind.JARM.value: "TLS fingerprint",
    CorrelationKind.CERT.value: "Certificate",
    CorrelationKind.CERT_ISSUER.value: "Certificate issuer",
    CorrelationKind.HEADERS.value: "Header set",
    CorrelationKind.TECH.value: "Technology",
    CorrelationKind.SERVER.value: "Server header",
    CorrelationKind.CDN.value: "CDN",
    CorrelationKind.ASN.value: "Network",
    CorrelationKind.TRACKING.value: "Tracking account",
}

CORRELATION_KIND_HELP: dict[str, str] = {
    CorrelationKind.IP.value: "Web assets resolving to the same IP address",
    CorrelationKind.CNAME.value: "Web assets aliased to the same CNAME target",
    CorrelationKind.TITLE.value: "Web assets responding with the same page title",
    CorrelationKind.FAVICON.value: "Web assets serving the same favicon hash",
    CorrelationKind.BODY.value: "Web assets returning an identical response body",
    CorrelationKind.SCREENSHOT.value: "Web assets whose screenshots render the same page",
    CorrelationKind.JARM.value: "Web assets with the same JARM TLS fingerprint",
    CorrelationKind.CERT.value: "Web assets presenting the same certificate",
    CorrelationKind.CERT_ISSUER.value: "Web assets presenting certificates from the same issuer",
    CorrelationKind.HEADERS.value: "Web assets returning an identical set of response headers",
    CorrelationKind.TECH.value: "Web assets fingerprinted with the same technology",
    CorrelationKind.SERVER.value: "Web assets returning the same Server header",
    CorrelationKind.CDN.value: "Web assets fronted by the same CDN or WAF",
    CorrelationKind.ASN.value: "Web assets announced by the same autonomous system",
    CorrelationKind.TRACKING.value: "Web assets sharing an analytics, tag manager or advertising account",
}

# after "N web assets"
CORRELATION_RELATION_PHRASE: dict[str, str] = {
    CorrelationKind.IP.value: "on the same address",
    CorrelationKind.CNAME.value: "with the same CNAME target",
    CorrelationKind.TITLE.value: "with the same page title",
    CorrelationKind.FAVICON.value: "with the same favicon",
    CorrelationKind.BODY.value: "with the same response body",
    CorrelationKind.SCREENSHOT.value: "rendering the same page",
    CorrelationKind.JARM.value: "with the same TLS fingerprint",
    CorrelationKind.CERT.value: "presenting the same certificate",
    CorrelationKind.CERT_ISSUER.value: "with the same certificate issuer",
    CorrelationKind.HEADERS.value: "with the same header set",
    CorrelationKind.TECH.value: "running the same technology",
    CorrelationKind.SERVER.value: "with the same Server header",
    CorrelationKind.CDN.value: "behind the same CDN",
    CorrelationKind.ASN.value: "in the same network",
    CorrelationKind.TRACKING.value: "sharing a tracking account",
}

# drawn by default
CORRELATION_DEFAULT_KINDS: frozenset[str] = frozenset(
    {
        CorrelationKind.IP.value,
        CorrelationKind.CNAME.value,
        CorrelationKind.TITLE.value,
        CorrelationKind.FAVICON.value,
        CorrelationKind.BODY.value,
        CorrelationKind.SCREENSHOT.value,
        CorrelationKind.JARM.value,
        CorrelationKind.CERT.value,
        CorrelationKind.TRACKING.value,
    }
)

CORRELATION_KIND_ORDER: tuple[str, ...] = tuple(k.value for k in CorrelationKind)


# a value shared with a host under another target, strongest first
CROSS_LINK_ORDER: tuple[str, ...] = (
    CorrelationKind.CERT.value,
    CorrelationKind.TRACKING.value,
    CorrelationKind.BODY.value,
    CorrelationKind.FAVICON.value,
    CorrelationKind.CNAME.value,
    CorrelationKind.TITLE.value,
)
# identities read off the page
CROSS_PAGE_KINDS: frozenset[str] = frozenset(
    {
        CorrelationKind.TITLE.value,
        CorrelationKind.FAVICON.value,
        CorrelationKind.BODY.value,
        CorrelationKind.TRACKING.value,
    }
)
MAX_CROSS_LINKS = 3
MAX_CROSS_PEERS = 6
MAX_CROSS_VALUES = 500
# the share of a project's targets past which a value is the estate's norm
CROSS_COMMON_TARGET_SHARE = 0.5
MIN_TARGETS_FOR_COMMON = 4
