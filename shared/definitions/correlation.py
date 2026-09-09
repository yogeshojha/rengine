"""The identities two hosts can share, and the noise rules that keep a shared identity meaningful."""

from __future__ import annotations

from enum import StrEnum

MAX_GRAPH_HOSTS = 3000
MAX_HUBS_PER_KIND = 80
MIN_SHARED = 2
# an identity most of the estate carries says nothing about any one host
COMMON_SHARE = 0.5


class CorrelationKind(StrEnum):
    IP = "ip"
    CNAME = "cname"
    TITLE = "title"
    FAVICON = "favicon"
    BODY = "content_hash"
    JARM = "jarm"
    CERT_ISSUER = "cert.issuer"
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
    CorrelationKind.CERT_ISSUER.value: "Certificate issuer",
    CorrelationKind.TECH.value: "Technology",
    CorrelationKind.SERVER.value: "Server header",
    CorrelationKind.CDN.value: "CDN",
}

CORRELATION_KIND_HELP: dict[str, str] = {
    CorrelationKind.IP.value: "Hosts that resolve to the same address share a box, a load balancer or an edge.",
    CorrelationKind.CNAME.value: "Hosts aliased to the same name sit on the same provider or service.",
    CorrelationKind.TITLE.value: "Hosts answering with the same page title are usually the same application.",
    CorrelationKind.FAVICON.value: "The same favicon hash is the same product, whatever the hostname says.",
    CorrelationKind.BODY.value: "An identical response body is the same page served under several names.",
    CorrelationKind.JARM.value: "The same TLS handshake fingerprint is the same server software and configuration.",
    CorrelationKind.CERT_ISSUER.value: "Certificates from the same issuer point at one procurement path.",
    CorrelationKind.TECH.value: "A shared technology. Common ones say little, rare ones say a lot.",
    CorrelationKind.SERVER.value: "The same Server header, version included.",
    CorrelationKind.CDN.value: "Fronted by the same CDN or WAF.",
}

# the identities strong enough to draw at rest; the rest are a click away
CORRELATION_DEFAULT_KINDS: frozenset[str] = frozenset(
    {
        CorrelationKind.IP.value,
        CorrelationKind.CNAME.value,
        CorrelationKind.TITLE.value,
        CorrelationKind.FAVICON.value,
        CorrelationKind.BODY.value,
        CorrelationKind.JARM.value,
    }
)

CORRELATION_KIND_ORDER: tuple[str, ...] = tuple(k.value for k in CorrelationKind)
