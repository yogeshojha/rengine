"""Hostnames resolving to third-party content or to a server with no site for them."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.estate import NEIGHBOUR_MAX_NAMES


class NameClaim(StrEnum):
    FOREIGN_SITE = "foreign_site"
    UNHOSTED = "unhosted"


class ClaimEvidence(StrEnum):
    REDIRECT = "redirect"
    CERTIFICATE = "certificate"
    LINKS = "links"
    ADDRESS_DEFAULT = "address_default"


CLAIM_TEMPLATES: dict[str, str] = {
    NameClaim.FOREIGN_SITE.value: "rengine-foreign-site",
    NameClaim.UNHOSTED.value: "rengine-unhosted-name",
}

CLAIM_TITLES: dict[str, str] = {
    NameClaim.FOREIGN_SITE.value: "Third-party content on hostname",
    NameClaim.UNHOSTED.value: "Dangling A record",
}

CLAIM_EVIDENCE_LABELS: dict[str, str] = {
    ClaimEvidence.REDIRECT.value: "Redirect",
    ClaimEvidence.CERTIFICATE.value: "Certificate",
    ClaimEvidence.LINKS.value: "Links",
    ClaimEvidence.ADDRESS_DEFAULT.value: "IP address response",
}

# independent kinds of evidence a claim needs
MIN_EVIDENCE = 2
# links to one domain that attribute the page to it
MIN_LINKS = 3
# a certificate naming more registrable domains than this is a platform's
MAX_CERT_DOMAINS = NEIGHBOUR_MAX_NAMES
# character-bigram overlap at which a host label and a domain label are one name
ALIAS_OVERLAP = 0.5
MIN_ALIAS_LABEL = 4
BODY_SCAN_BYTES = 300_000
STREAM_BATCH = 200
LOCAL_SUFFIXES: frozenset[str] = frozenset(
    {
        "local",
        "localdomain",
        "localhost",
        "internal",
        "lan",
        "home",
        "test",
        "default",
        "invalid",
    }
)
