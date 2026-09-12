"""How two targets in one project can be shown to belong together."""

from __future__ import annotations

from enum import StrEnum


class TargetRelation(StrEnum):
    CERTIFICATE = "certificate"
    REGISTRANT = "registrant_name"
    NETWORK = "network"
    NAMESERVER = "nameserver"
    DNS_RECORD = "dns_record"
    NETWORK_CIDR = "network_cidr"
    FAVICON = "favicon"


# strongest first
RELATION_ORDER: tuple[str, ...] = (
    TargetRelation.CERTIFICATE.value,
    TargetRelation.REGISTRANT.value,
    TargetRelation.NETWORK.value,
    TargetRelation.NAMESERVER.value,
    TargetRelation.DNS_RECORD.value,
    TargetRelation.NETWORK_CIDR.value,
    TargetRelation.FAVICON.value,
)

RELATION_LABELS: dict[str, str] = {
    TargetRelation.CERTIFICATE.value: "Certificate",
    TargetRelation.REGISTRANT.value: "Registrant",
    TargetRelation.NETWORK.value: "Network",
    TargetRelation.NAMESERVER.value: "Nameserver",
    TargetRelation.DNS_RECORD.value: "DNS record",
    TargetRelation.NETWORK_CIDR.value: "Network block",
    TargetRelation.FAVICON.value: "Favicon",
}

RELATION_HELP: dict[str, str] = {
    TargetRelation.CERTIFICATE.value: "One certificate names both targets",
    TargetRelation.REGISTRANT.value: "Registered to the same name",
    TargetRelation.NETWORK.value: "Addresses in a network the organisation runs",
    TargetRelation.NAMESERVER.value: "Answered by the same nameserver",
    TargetRelation.DNS_RECORD.value: "A DNS record nobody rents, on both targets",
    TargetRelation.NETWORK_CIDR.value: "Inside the same registered network block",
    TargetRelation.FAVICON.value: "Serving the same favicon",
}

MAX_RELATED_TARGETS = 50
MAX_RELATION_EVIDENCE = 8
MAX_SAN_ROWS = 5000
MAX_COVERED_PROGRAMS = 20
# a favicon on more estates than this is a framework's, not an owner's
FAVICON_MAX_TARGETS = 4
