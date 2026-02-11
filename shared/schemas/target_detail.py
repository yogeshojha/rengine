import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.models.bgp_summary import BgpSummaryRead
from shared.models.dns import DnsLookupRead
from shared.models.organization import OrganizationSummary
from shared.models.tag import TagSummary
from shared.models.whois import WhoisRecordRead


class AnnouncedPrefixDetail(BaseModel):
    prefix: str
    ip_version: int = 4
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class ASNNeighbourDetail(BaseModel):
    neighbour_asn: int
    relationship: str
    power: int = 0


class ASOverviewDetail(BaseModel):
    asn: int
    holder: str = ""
    rir: str | None = None
    announced: bool = False
    block_name: str | None = None
    block_resource: str | None = None


class NetworkInfoDetail(BaseModel):
    ip: str
    prefix: str = ""
    asn: int = 0


class PrefixOverviewDetail(BaseModel):
    prefix: str
    asn: int
    holder: str = ""
    is_announced: bool = True


class RelatedPrefixDetail(BaseModel):
    related_prefix: str
    relationship: str
    origin_asn: int | None = None


class AbuseContactDetail(BaseModel):
    resource: str
    abuse_email: str
    rir: str | None = None


class TargetBgpDetailResponse(BaseModel):
    """Full BGP enrichment data for a target."""

    target_id: uuid.UUID
    target_type: TargetType
    status: TaskStatus
    summary: BgpSummaryRead | None = None
    as_overview: ASOverviewDetail | None = None
    announced_prefixes: list[AnnouncedPrefixDetail] = Field(default_factory=list)
    neighbours: list[ASNNeighbourDetail] = Field(default_factory=list)
    network_info: list[NetworkInfoDetail] = Field(default_factory=list)
    prefix_overview: list[PrefixOverviewDetail] = Field(default_factory=list)
    related_prefixes: list[RelatedPrefixDetail] = Field(default_factory=list)
    abuse_contacts: list[AbuseContactDetail] = Field(default_factory=list)


class TargetDnsDetailResponse(BaseModel):
    target_id: uuid.UUID
    target_type: TargetType
    status: TaskStatus
    error: str | None = None
    lookup: DnsLookupRead | None = None


class TargetWhoisDetailResponse(BaseModel):
    target_id: uuid.UUID
    target_type: TargetType
    status: TaskStatus
    error: str | None = None
    record: WhoisRecordRead | None = None


class TargetDetailRead(BaseModel):
    id: uuid.UUID
    target_value: str
    display_name: str | None = None
    target_type: TargetType
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID
    organizations: list[OrganizationSummary] = Field(default_factory=list)
    tags: list[TagSummary] = Field(default_factory=list)

    whois_status: TaskStatus
    whois_error: str | None = None
    whois: WhoisRecordRead | None = None

    dns_status: TaskStatus
    dns_error: str | None = None
    dns: DnsLookupRead | None = None

    bgp_status: TaskStatus
    bgp: TargetBgpDetailResponse | None = None


class EnrichmentRefreshResponse(BaseModel):
    target_id: uuid.UUID
    enrichment_type: str
    status: str
    message: str
