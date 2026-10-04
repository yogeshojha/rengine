from enum import Enum, StrEnum


class TargetType(Enum):
    DOMAIN = "domain"
    IP = "ip"
    IP_RANGE = "ip_range"
    ASN = "asn"
    URL = "url"


HOSTNAME_TARGET_TYPES = frozenset({TargetType.DOMAIN, TargetType.URL})
NETWORK_TARGET_TYPES = frozenset({TargetType.IP, TargetType.IP_RANGE, TargetType.ASN})


class EnrichmentKind(StrEnum):
    WHOIS = "whois"
    DNS = "dns"
    BGP = "bgp"
    INFOSTEALER = "infostealer"
