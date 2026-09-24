"""Owned names answered by a server that does not host them."""

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
    NameClaim.FOREIGN_SITE.value: "Name serves another organisation's site",
    NameClaim.UNHOSTED.value: "Name points at a server that does not host it",
}

CLAIM_EVIDENCE_LABELS: dict[str, str] = {
    ClaimEvidence.REDIRECT.value: "Redirects to",
    ClaimEvidence.CERTIFICATE.value: "Presents the certificate for",
    ClaimEvidence.LINKS.value: "Links to",
    ClaimEvidence.ADDRESS_DEFAULT.value: "Same page as the bare address",
}

# independent kinds of evidence a claim needs
MIN_EVIDENCE = 2
# links to one domain before the page is read as that domain's
MIN_LINKS = 3
# a certificate naming more registrable domains than this is a platform's
MAX_CERT_DOMAINS = NEIGHBOUR_MAX_NAMES
# character-bigram overlap at which a host label and a domain label are one name
ALIAS_OVERLAP = 0.5
MIN_ALIAS_LABEL = 4
BODY_SCAN_BYTES = 300_000
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
