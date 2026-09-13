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
}

CORRELATION_KIND_HELP: dict[str, str] = {
    CorrelationKind.IP.value: "Hosts resolving to the same IP address",
    CorrelationKind.CNAME.value: "Hosts aliased to the same CNAME target",
    CorrelationKind.TITLE.value: "Hosts responding with the same page title",
    CorrelationKind.FAVICON.value: "Hosts serving the same favicon hash",
    CorrelationKind.BODY.value: "Hosts returning an identical response body",
    CorrelationKind.SCREENSHOT.value: "Hosts whose screenshots render the same page",
    CorrelationKind.JARM.value: "Hosts with the same JARM TLS fingerprint",
    CorrelationKind.CERT.value: "Hosts presenting the same certificate",
    CorrelationKind.CERT_ISSUER.value: "Hosts presenting certificates from the same issuer",
    CorrelationKind.HEADERS.value: "Hosts returning an identical set of response headers",
    CorrelationKind.TECH.value: "Hosts fingerprinted with the same technology",
    CorrelationKind.SERVER.value: "Hosts returning the same Server header",
    CorrelationKind.CDN.value: "Hosts fronted by the same CDN or WAF",
    CorrelationKind.ASN.value: "Hosts announced by the same autonomous system",
}

# what a set of hosts sharing this identity does, after "N hosts"
CORRELATION_RELATION_PHRASE: dict[str, str] = {
    CorrelationKind.IP.value: "resolve to the same address",
    CorrelationKind.CNAME.value: "share a CNAME target",
    CorrelationKind.TITLE.value: "show the same page title",
    CorrelationKind.FAVICON.value: "serve the same favicon",
    CorrelationKind.BODY.value: "return the same response body",
    CorrelationKind.SCREENSHOT.value: "render the same page",
    CorrelationKind.JARM.value: "share a TLS fingerprint",
    CorrelationKind.CERT.value: "present the same certificate",
    CorrelationKind.CERT_ISSUER.value: "share a certificate issuer",
    CorrelationKind.HEADERS.value: "return the same header set",
    CorrelationKind.TECH.value: "run the same technology",
    CorrelationKind.SERVER.value: "return the same Server header",
    CorrelationKind.CDN.value: "sit behind the same CDN",
    CorrelationKind.ASN.value: "sit in the same network",
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
    }
)

CORRELATION_KIND_ORDER: tuple[str, ...] = tuple(k.value for k in CorrelationKind)


# a value shared with a host under another target, strongest first
CROSS_LINK_ORDER: tuple[str, ...] = (
    CorrelationKind.CERT.value,
    CorrelationKind.BODY.value,
    CorrelationKind.FAVICON.value,
    CorrelationKind.CNAME.value,
    CorrelationKind.IP.value,
    CorrelationKind.TITLE.value,
)
CROSS_LINK_KINDS: frozenset[str] = frozenset(CROSS_LINK_ORDER)
# identities read off the page
CROSS_PAGE_KINDS: frozenset[str] = frozenset(
    {
        CorrelationKind.TITLE.value,
        CorrelationKind.FAVICON.value,
        CorrelationKind.BODY.value,
    }
)
MAX_CROSS_LINKS = 3
MAX_CROSS_PEERS = 6
MAX_CROSS_VALUES = 500
# the share of a project's targets past which a value is the estate's norm
CROSS_COMMON_TARGET_SHARE = 0.5
MIN_TARGETS_FOR_COMMON = 4
