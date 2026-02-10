from datetime import datetime

from pydantic import BaseModel, Field

from shared.enums.ripestat import RIPEStatLookupType


class AnnouncedPrefix(BaseModel):
    prefix: str
    ip_version: int = 4
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class AnnouncedPrefixesResponse(BaseModel):
    asn: int
    prefixes: list[AnnouncedPrefix] = Field(default_factory=list)


class ASNNeighbour(BaseModel):
    asn: int
    relationship: str  # upstream / downstream / uncertain
    power: int = 0


class ASNNeighboursResponse(BaseModel):
    asn: int
    neighbours: list[ASNNeighbour] = Field(default_factory=list)


class ASOverviewResponse(BaseModel):
    asn: int
    holder: str = ""
    rir: str | None = None
    announced: bool = False
    block_name: str | None = None
    block_resource: str | None = None


class NetworkInfoResponse(BaseModel):
    ip: str
    prefix: str | None = None
    asns: list[int] = Field(default_factory=list)


class AbuseContactResponse(BaseModel):
    resource: str
    abuse_emails: list[str] = Field(default_factory=list)
    rir: str | None = None


class PrefixOverviewASN(BaseModel):
    asn: int
    holder: str = ""


class PrefixOverviewResponse(BaseModel):
    prefix: str
    asns: list[PrefixOverviewASN] = Field(default_factory=list)
    is_announced: bool = False


class RelatedPrefixEntry(BaseModel):
    prefix: str
    relationship: str  # overlap / more_specific / less_specific
    origin_asn: int | None = None


class RelatedPrefixesResponse(BaseModel):
    prefix: str
    related: list[RelatedPrefixEntry] = Field(default_factory=list)


class AnnouncedPrefixRead(BaseModel):
    prefix: str
    ip_version: int
    first_seen: datetime | None
    last_seen: datetime | None


class ASNNeighbourRead(BaseModel):
    neighbour_asn: int
    relationship: str
    power: int


class ASOverviewRead(BaseModel):
    asn: int
    holder: str
    rir: str | None
    announced: bool
    block_name: str | None
    block_resource: str | None


class NetworkInfoRead(BaseModel):
    ip: str
    prefix: str
    asn: int


class AbuseContactRead(BaseModel):
    resource: str
    abuse_emails: list[str]
    rir: str | None


class PrefixOverviewRead(BaseModel):
    prefix: str
    asn: int
    holder: str
    is_announced: bool


class RelatedPrefixRead(BaseModel):
    related_prefix: str
    relationship: str
    origin_asn: int | None


# Generic wrapper for all lookup responses, includes cache metadata
class RIPEStatResult(BaseModel):
    lookup_type: RIPEStatLookupType
    query_value: str
    result_count: int
    cached: bool = False
    queried_at: datetime | None = None
    data: (
        list[AnnouncedPrefixRead]
        | list[ASNNeighbourRead]
        | ASOverviewRead
        | list[NetworkInfoRead]
        | AbuseContactRead
        | list[PrefixOverviewRead]
        | list[RelatedPrefixRead]
    )
