import uuid

from pydantic import BaseModel, Field

from shared.definitions.asset_query import MAX_QUERY_LENGTH
from shared.models.asset_query import QueryError
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
    single_source: int = 0
    resolution: list[Bucket] = Field(default_factory=list)
    status_reframe: list[Bucket] = Field(default_factory=list)
    cert_buckets: list[Bucket] = Field(default_factory=list)
    top_tech: list[Tally] = Field(default_factory=list)
    tech_total: int = 0
    top_asn: list[Tally] = Field(default_factory=list)
    geography: list[Tally] = Field(default_factory=list)
    geo_total: int = 0
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
    total_capped: bool = False
    error: QueryError | None = None


class IpGroupFilter(BaseModel):
    q: str | None = Field(default=None, max_length=MAX_QUERY_LENGTH)
    exposure: list[str] = Field(default_factory=list, max_length=4)
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
    sort: str = Field(default="hosts", max_length=20)
    order: str = Field(default="desc", max_length=4)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=100_000_000)

    def has_facets(self) -> bool:
        return bool(
            self.exposure
            or self.asns
            or self.countries
            or self.ports
            or self.services
            or self.cdn != "any"
            or self.alive != "any"
            or self.version
            or self.sensitive
            or self.hosted
            or self.open
        )


class IpFacets(BaseModel):
    exposure: list[Facet] = Field(default_factory=list)
    asn: list[Facet] = Field(default_factory=list)
    country: list[Facet] = Field(default_factory=list)
    port: list[Facet] = Field(default_factory=list)
    service: list[Facet] = Field(default_factory=list)


class ServiceRead(BaseModel):
    id: uuid.UUID
    ip: str
    port: int
    protocol: str
    state: str
    service_name: str | None = None
    service_class: str
    source: str
    is_http: bool = False
    tls: bool = False
    product: str | None = None
    version: str | None = None
    banner: str | None = None
    asn: int | None = None
    asn_org: str | None = None
    country: str | None = None
    prefix: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    scan_policy: str | None = None
    host_count: int = 0
    hosts: list[str] = Field(default_factory=list)
    web_count: int = 0
    status_code: int | None = None
    url: str | None = None
    title: str | None = None
    is_sensitive: bool = False
    is_new: bool = False


class ServicePage(BaseModel):
    items: list[ServiceRead] = Field(default_factory=list)
    total: int = 0
    total_capped: bool = False
    error: QueryError | None = None


class ServiceFilter(BaseModel):
    q: str | None = Field(default=None, max_length=MAX_QUERY_LENGTH)
    classes: list[str] = Field(default_factory=list, max_length=10)
    ports: list[int] = Field(default_factory=list, max_length=200)
    services: list[str] = Field(default_factory=list, max_length=200)
    sources: list[str] = Field(default_factory=list, max_length=10)
    asns: list[int] = Field(default_factory=list, max_length=100)
    countries: list[str] = Field(default_factory=list, max_length=100)
    cdn: str = Field(default="any", max_length=10)
    http: str = Field(default="any", max_length=10)
    sensitive: bool = False
    named: bool = False
    new: bool = False
    sort: str = Field(default="exposure", max_length=20)
    order: str = Field(default="desc", max_length=4)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=100_000_000)

    def has_facets(self) -> bool:
        return bool(
            self.classes
            or self.ports
            or self.services
            or self.sources
            or self.asns
            or self.countries
            or self.cdn != "any"
            or self.http != "any"
            or self.sensitive
            or self.named
            or self.new
        )


class ServiceFacets(BaseModel):
    klass: list[Facet] = Field(default_factory=list, serialization_alias="class")
    port: list[Facet] = Field(default_factory=list)
    service: list[Facet] = Field(default_factory=list)
    source: list[Facet] = Field(default_factory=list)
    asn: list[Facet] = Field(default_factory=list)
    country: list[Facet] = Field(default_factory=list)


class ExposureBand(BaseModel):
    key: str
    label: str
    count: int
    addresses: int
    query: str


class ExposureLine(BaseModel):
    key: str
    label: str
    detail: str | None = None
    count: int
    query: str


class ScanExposure(BaseModel):
    services: int = 0
    addresses: int = 0
    web_services: int = 0
    non_web_services: int = 0
    answering_http: int = 0
    sensitive: int = 0
    named: int = 0
    passive_only: int = 0
    nonstandard_web: int = 0
    bands: list[ExposureBand] = Field(default_factory=list)
    top_services: list[ExposureLine] = Field(default_factory=list)
    coverage: list[ExposureLine] = Field(default_factory=list)
    scanned: int = 0
