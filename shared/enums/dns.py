from enum import Enum


class DnsRecordType(Enum):
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    NS = "NS"
    MX = "MX"
    TXT = "TXT"
    SOA = "SOA"
    SRV = "SRV"
    PTR = "PTR"
    CAA = "CAA"
    AXFR = "AXFR"
    CDN = "CDN"
