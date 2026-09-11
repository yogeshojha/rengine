"""Identity kinds two hosts can share, and the thresholds that make a shared identity significant."""

from __future__ import annotations

from enum import StrEnum

MAX_GRAPH_HOSTS = 3000
MAX_HUBS_PER_KIND = 80
MIN_SHARED = 2
# hidden by default at or above this share
COMMON_SHARE = 0.5
MIN_ESTATE_FOR_COMMON = 25


class CorrelationKind(StrEnum):
    IP = "ip"
    CNAME = "cname"
    TITLE = "title"
    FAVICON = "favicon"
    BODY = "content_hash"
    JARM = "jarm"
    CERT = "cert.fingerprint"
    CERT_ISSUER = "cert.issuer"
    HEADERS = "header_hash"
    TECH = "tech"
    SERVER = "server"
    CDN = "cdn"


CORRELATION_KIND_LABELS: dict[str, str] = {
    CorrelationKind.IP.value: "Address",
    CorrelationKind.CNAME.value: "CNAME target",
    CorrelationKind.TITLE.value: "Page title",
    CorrelationKind.FAVICON.value: "Favicon",
    CorrelationKind.BODY.value: "Body hash",
    CorrelationKind.JARM.value: "TLS fingerprint",
    CorrelationKind.CERT.value: "Certificate",
    CorrelationKind.CERT_ISSUER.value: "Certificate issuer",
    CorrelationKind.HEADERS.value: "Header set",
    CorrelationKind.TECH.value: "Technology",
    CorrelationKind.SERVER.value: "Server header",
    CorrelationKind.CDN.value: "CDN",
}

CORRELATION_KIND_HELP: dict[str, str] = {
    CorrelationKind.IP.value: "Hosts resolving to the same IP address",
    CorrelationKind.CNAME.value: "Hosts aliased to the same CNAME target",
    CorrelationKind.TITLE.value: "Hosts responding with the same page title",
    CorrelationKind.FAVICON.value: "Hosts serving the same favicon hash",
    CorrelationKind.BODY.value: "Hosts returning an identical response body",
    CorrelationKind.JARM.value: "Hosts with the same JARM TLS fingerprint",
    CorrelationKind.CERT.value: "Hosts presenting the same certificate",
    CorrelationKind.CERT_ISSUER.value: "Hosts presenting certificates from the same issuer",
    CorrelationKind.HEADERS.value: "Hosts returning an identical set of response headers",
    CorrelationKind.TECH.value: "Hosts fingerprinted with the same technology",
    CorrelationKind.SERVER.value: "Hosts returning the same Server header",
    CorrelationKind.CDN.value: "Hosts fronted by the same CDN or WAF",
}

# drawn by default
CORRELATION_DEFAULT_KINDS: frozenset[str] = frozenset(
    {
        CorrelationKind.IP.value,
        CorrelationKind.CNAME.value,
        CorrelationKind.TITLE.value,
        CorrelationKind.FAVICON.value,
        CorrelationKind.BODY.value,
        CorrelationKind.JARM.value,
        CorrelationKind.CERT.value,
    }
)

CORRELATION_KIND_ORDER: tuple[str, ...] = tuple(k.value for k in CorrelationKind)
