from pydantic import BaseModel, Field

from shared.models.http_asset import HttpAssetRead
from shared.models.ip_address import IpAddressRead
from shared.models.port import PortRead
from shared.models.subdomain import Facet, SubdomainRelation


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
    sources: list[Tally] = Field(default_factory=list)
    resolution: list[Bucket] = Field(default_factory=list)
    status_reframe: list[Bucket] = Field(default_factory=list)
    cert_buckets: list[Bucket] = Field(default_factory=list)
    top_tech: list[Tally] = Field(default_factory=list)
    tech_total: int = 0
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
    port_count: int = 0
    has_sensitive: bool = False
    asset_count: int = 0


class IpGroupPage(BaseModel):
    items: list[IpGroupRead] = Field(default_factory=list)
    total: int = 0


class IpGroupFilter(BaseModel):
    text: str | None = Field(default=None, max_length=200)
    asns: list[int] = Field(default_factory=list, max_length=100)
    countries: list[str] = Field(default_factory=list, max_length=100)
    ports: list[int] = Field(default_factory=list, max_length=200)
    services: list[str] = Field(default_factory=list, max_length=200)
    cdn: str = Field(default="any", max_length=10)
    alive: str = Field(default="any", max_length=10)
    version: int = Field(default=0, ge=0, le=6)
    sensitive: bool = False
    hosted: bool = False
    open: bool = False
    host: str | None = Field(default=None, max_length=253)
    ptr: str | None = Field(default=None, max_length=253)
    org: str | None = Field(default=None, max_length=200)
    prefix: str | None = Field(default=None, max_length=64)
    sort: str = Field(default="ip", max_length=20)
    order: str = Field(default="asc", max_length=4)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=100_000_000)


class IpFacets(BaseModel):
    asn: list[Facet] = Field(default_factory=list)
    country: list[Facet] = Field(default_factory=list)
    port: list[Facet] = Field(default_factory=list)
    service: list[Facet] = Field(default_factory=list)
