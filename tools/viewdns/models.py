from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ViewDNSLookupType(StrEnum):
    IP_HISTORY = "ip_history"
    REVERSE_IP = "reverse_ip"
    REVERSE_NS = "reverse_ns"
    REVERSE_WHOIS = "reverse_whois"


class IPHistoryRecord(BaseModel):
    ip: str = ""
    location: str = ""
    owner: str = ""
    last_seen: date | None = None


class IPHistoryResponse(BaseModel):
    lookup_type: ViewDNSLookupType = ViewDNSLookupType.IP_HISTORY
    domain: str
    records: list[IPHistoryRecord] = Field(default_factory=list)

    @property
    def unique_ips(self) -> list[str]:
        return list({r.ip for r in self.records if r.ip})


class ReverseIPDomain(BaseModel):
    name: str = ""
    last_resolved: date | None = None


class ReverseIPResponse(BaseModel):
    lookup_type: ViewDNSLookupType = ViewDNSLookupType.REVERSE_IP
    host: str
    domain_count: int = 0
    domains: list[ReverseIPDomain] = Field(default_factory=list)


class ReverseNSDomain(BaseModel):
    domain: str = ""


class ReverseNSResponse(BaseModel):
    lookup_type: ViewDNSLookupType = ViewDNSLookupType.REVERSE_NS
    nameserver: str
    domain_count: int = 0
    domains: list[ReverseNSDomain] = Field(default_factory=list)


class ReverseWhoisMatch(BaseModel):
    domain: str = ""
    created_date: date | None = None
    registrar: str = ""


class ReverseWhoisResponse(BaseModel):
    lookup_type: ViewDNSLookupType = ViewDNSLookupType.REVERSE_WHOIS
    query: str
    result_count: int = 0
    matches: list[ReverseWhoisMatch] = Field(default_factory=list)


ViewDNSResponse = (
    IPHistoryResponse | ReverseIPResponse | ReverseNSResponse | ReverseWhoisResponse
)


# readmodel for FE


class ViewDNSCacheRead(BaseModel):
    lookup_type: ViewDNSLookupType
    query_value: str
    result_count: int
    cached: bool = False
    queried_at: datetime | None = None
    data: ViewDNSResponse
