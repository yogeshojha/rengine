from enum import Enum


class WhoisLookupType(Enum):
    DOMAIN = "DOMAIN"
    IP = "IP"
    ASN = "ASN"


class WhoisStatus(Enum):
    PENDING = "pending"
    QUERYING = "querying"
    SUCCESS = "success"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
