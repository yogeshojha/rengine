from enum import Enum


class IpSource(Enum):
    SEED = "seed"
    CIDR_EXPANSION = "cidr_expansion"
    ASN_EXPANSION = "asn_expansion"
    DNS_RESOLUTION = "dns_resolution"
    REVERSE_DNS = "reverse_dns"
