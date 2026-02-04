from enum import Enum


class TargetType(str, Enum):
    DOMAIN = "domain"
    IP = "ip"
    IP_RANGE = "ip_range"
    ASN = "asn"
    URL = "url"
