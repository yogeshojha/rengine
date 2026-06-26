from pydantic import BaseModel, Field

from shared.models.http_asset import HttpAssetRead
from shared.models.ip_address import IpAddressRead
from shared.models.port import PortRead
from shared.models.subdomain import SubdomainRelation


class SurfaceStat(BaseModel):
    key: str
    label: str
    value: int
    filter: str = ""


class AttentionItem(BaseModel):
    key: str
    label: str
    count: int
    filter: str
    tone: str


class Bucket(BaseModel):
    key: str
    label: str
    count: int
    klass: str


class Tally(BaseModel):
    name: str
    count: int


class ClusterStat(BaseModel):
    kind: str
    reason: str
    value: str
    count: int


class SubdomainInsights(BaseModel):
    surface: list[SurfaceStat] = Field(default_factory=list)
    attention: list[AttentionItem] = Field(default_factory=list)
    status_reframe: list[Bucket] = Field(default_factory=list)
    cert_buckets: list[Bucket] = Field(default_factory=list)
    top_tech: list[Tally] = Field(default_factory=list)
    top_asn: list[Tally] = Field(default_factory=list)
    services: list[Tally] = Field(default_factory=list)
    clusters: list[ClusterStat] = Field(default_factory=list)


class SubdomainCorrelation(BaseModel):
    primary_asset: HttpAssetRead | None = None
    services: list[HttpAssetRead] = Field(default_factory=list)
    ports: list[PortRead] = Field(default_factory=list)
    ip_metas: list[IpAddressRead] = Field(default_factory=list)
    related: list[SubdomainRelation] = Field(default_factory=list)


class IpGroupRead(BaseModel):
    ip: str
    version: int
    asn: int | None = None
    asn_org: str | None = None
    country: str | None = None
    prefix: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    is_alive: bool | None = None
    ptr_hostnames: list[str] = Field(default_factory=list)
    ports: list[PortRead] = Field(default_factory=list)
    host_count: int = 0
    hosts: list[str] = Field(default_factory=list)


class IpGroupPage(BaseModel):
    items: list[IpGroupRead] = Field(default_factory=list)
    total: int = 0
