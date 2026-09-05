import uuid
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.asset_query import MAX_QUERY_LENGTH
from shared.definitions.endpoints import (
    EndpointClass,
    EndpointSource,
)
from shared.definitions.vulnerabilities import CoverageStatus
from shared.models.asset_query import MatchEvidence, QueryError
from shared.utils.datetime import utc_now


def _json_list() -> Field:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


def _json_dict() -> Field:
    return Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


def _text() -> Field:
    return Field(default=None, sa_column=Column(Text, nullable=True))


class Endpoint(SQLModel, table=True):
    __tablename__ = "endpoints"
    __table_args__ = (
        UniqueConstraint("scan_id", "signature", name="uq_endpoint_scan_signature"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    # structural identity: path shape plus parameter names, never parameter values
    signature: str = Field(max_length=64, index=True)

    # where it is
    url: str = Field(max_length=2000)
    host: str = Field(max_length=500, index=True)
    port: int = Field(default=443)
    scheme: str = Field(default="https", max_length=8)
    path: str = Field(max_length=1500)
    dir_path: str = Field(max_length=1500, index=True)
    filename: str | None = Field(default=None, max_length=300)
    extension: str | None = Field(default=None, max_length=10, index=True)
    depth: int = Field(default=0, index=True)

    # what it accepts
    params: list = _json_list()
    param_count: int = Field(default=0, index=True)
    param_samples: list = _json_list()
    variants: int = Field(default=1)
    more_variants: bool = Field(default=False)
    methods: list = _json_list()

    # who says so
    sources: list = _json_list()
    primary_source: str = Field(
        default=EndpointSource.OTHER.value, max_length=24, index=True
    )
    discovery: dict = _json_dict()
    found_on: str | None = Field(default=None, max_length=2000)

    # what it answered, if anything asked
    is_probed: bool = Field(default=False, index=True)
    status_code: int | None = Field(default=None, index=True)
    content_type: str | None = Field(default=None, max_length=255)
    content_length: int | None = Field(default=None)
    title: str | None = Field(default=None, max_length=1000)
    words: int | None = Field(default=None)
    lines: int | None = Field(default=None)
    response_time: float | None = Field(default=None)
    redirect_location: str | None = Field(default=None, max_length=2000)
    content_hash: str | None = Field(default=None, max_length=80, index=True)
    tech: list = _json_list()

    # how it reads
    endpoint_class: str = Field(
        default=EndpointClass.OTHER.value, max_length=16, index=True
    )
    interest: list = _json_list()

    # correlation ids, resolved at write time; no FK so a row outlives its asset
    http_asset_id: uuid.UUID | None = Field(default=None, index=True)
    subdomain_id: uuid.UUID | None = Field(default=None, index=True)

    archive_last_seen: datetime | None = Field(default=None)
    discovered_at: datetime = Field(default_factory=utc_now, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class EndpointCoverage(SQLModel, table=True):
    """One provider's account of what it covered. A null count means unknown, never zero."""

    __tablename__ = "endpoint_coverage"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    source: str = Field(max_length=24, index=True)
    tool: str | None = Field(default=None, max_length=40)
    status: str = Field(default=CoverageStatus.COMPLETED.value, max_length=16)

    hosts_total: int = Field(default=0)
    hosts_scanned: int | None = Field(default=None)
    hosts_dropped: list = _json_list()
    urls_found: int | None = Field(default=None)
    urls_stored: int | None = Field(default=None)
    urls_probed: int | None = Field(default=None)
    pages_fetched: int | None = Field(default=None)
    depth_reached: int | None = Field(default=None)
    errors: int | None = Field(default=None)
    capped: bool = Field(default=False)
    cap_reason: str | None = Field(default=None, max_length=200)

    command: str | None = _text()
    error: str | None = Field(default=None, max_length=2000)

    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = Field(default=None)
    duration_seconds: float | None = Field(default=None)


class SourceEvidence(BaseModel):
    """Why one provider believes this endpoint exists."""

    source: str
    label: str
    kind: str
    detail: str | None = None
    found_on: str | None = None
    observed_at: datetime | None = None


class EndpointRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    signature: str
    url: str
    host: str
    port: int
    scheme: str
    path: str
    dir_path: str
    filename: str | None = None
    extension: str | None = None
    depth: int
    params: list[str] = PydanticField(default_factory=list)
    param_count: int = 0
    variants: int = 1
    more_variants: bool = False
    methods: list[str] = PydanticField(default_factory=list)
    sources: list[str] = PydanticField(default_factory=list)
    primary_source: str
    evidence: list[SourceEvidence] = PydanticField(default_factory=list)
    found_on: str | None = None
    is_probed: bool = False
    status_code: int | None = None
    content_type: str | None = None
    content_length: int | None = None
    title: str | None = None
    words: int | None = None
    lines: int | None = None
    response_time: float | None = None
    redirect_location: str | None = None
    tech: list[str] = PydanticField(default_factory=list)
    endpoint_class: str
    interest: list[str] = PydanticField(default_factory=list)
    http_asset_id: uuid.UUID | None = None
    subdomain_id: uuid.UUID | None = None
    archive_last_seen: datetime | None = None
    discovered_at: datetime
    is_new: bool = False
    matched_in: list[MatchEvidence] = PydanticField(default_factory=list)


class EndpointDetail(EndpointRead):
    param_samples: list = PydanticField(default_factory=list)
    discovery: dict = PydanticField(default_factory=dict)
    content_hash: str | None = None
    siblings: int = 0


class EndpointFilter(BaseModel):
    q: str | None = PydanticField(default=None, max_length=MAX_QUERY_LENGTH)
    host: str | None = None
    dir_path: str | None = None
    subtree: bool = True
    endpoint_class: str | None = None
    source: str | None = None
    interest: str | None = None
    status_class: str | None = None
    probed: bool | None = None
    new: bool = False
    hide_static: bool = False
    sort: str = "path"
    direction: str = "asc"
    page: int = 1
    size: int = 50

    def has_facets(self) -> bool:
        return any(
            (
                self.host,
                self.dir_path,
                self.endpoint_class,
                self.source,
                self.interest,
                self.status_class,
                self.probed is not None,
                self.new,
                self.hide_static,
            )
        )


class EndpointPage(BaseModel):
    items: list[EndpointRead] = PydanticField(default_factory=list)
    total: int = 0
    total_capped: bool = False
    page: int = 1
    size: int = 50
    error: QueryError | None = None


class EndpointFacet(BaseModel):
    value: str
    label: str
    count: int


class EndpointFacets(BaseModel):
    endpoint_class: list[EndpointFacet] = PydanticField(default_factory=list)
    source: list[EndpointFacet] = PydanticField(default_factory=list)
    interest: list[EndpointFacet] = PydanticField(default_factory=list)
    status_class: list[EndpointFacet] = PydanticField(default_factory=list)
    extension: list[EndpointFacet] = PydanticField(default_factory=list)
    host: list[EndpointFacet] = PydanticField(default_factory=list)
    total: int = 0
    static_total: int = 0


class TreeLeaf(BaseModel):
    """The one endpoint a folder holds when that folder is only its own index."""

    id: uuid.UUID
    url: str
    host: str
    path: str
    params: list[str] = PydanticField(default_factory=list)
    param_count: int = 0
    endpoint_class: str
    is_probed: bool = False
    status_code: int | None = None
    content_length: int | None = None
    sources: list[str] = PydanticField(default_factory=list)
    interest: list[str] = PydanticField(default_factory=list)


class TreeNode(BaseModel):
    """One directory or host in the site tree, counted through the same filter as the table."""

    key: str
    name: str
    path: str
    host: str | None = None
    kind: str = "directory"
    depth: int = 0
    direct_count: int = 0
    subtree_count: int = 0
    child_count: int = 0
    hosts: int = 1
    status_mix: dict[str, int] = PydanticField(default_factory=dict)
    class_mix: dict[str, int] = PydanticField(default_factory=dict)
    sources: list[str] = PydanticField(default_factory=list)
    interest: list[str] = PydanticField(default_factory=list)
    has_params: bool = False
    params: int = 0
    verified: int = 0
    unprobed: int = 0
    new_count: int = 0
    gone_count: int = 0
    anomaly: str | None = None
    archive_only: bool = False
    glyph: str = "folder"
    sample_url: str | None = None
    leaf: TreeLeaf | None = None
    query: str
    children: list["TreeNode"] = PydanticField(default_factory=list)
    lazy: bool = False
    folders: int = 0
    top_folders: list[str] = PydanticField(default_factory=list)


class HostPage(BaseModel):
    """One page of hosts with their rollups; a host's folders load when it is opened."""

    items: list[TreeNode] = PydanticField(default_factory=list)
    total: int = 0
    total_endpoints: int = 0
    page: int = 1
    size: int = 50
    error: QueryError | None = None


class MergedLeaf(BaseModel):
    """One path inside a folder, folded across every host that serves it."""

    key: str
    path: str
    name: str
    params: list[str] = PydanticField(default_factory=list)
    param_count: int = 0
    endpoint_class: str
    hosts: int = 0
    endpoints: int = 0
    status_mix: dict[str, int] = PydanticField(default_factory=dict)
    unprobed: int = 0
    interest: list[str] = PydanticField(default_factory=list)
    sources: list[str] = PydanticField(default_factory=list)
    host_names: list[str] = PydanticField(default_factory=list)
    new_count: int = 0
    sample_id: uuid.UUID
    sample_url: str
    sample_status: int | None = None
    query: str


class MergedLeafPage(BaseModel):
    items: list[MergedLeaf] = PydanticField(default_factory=list)
    total: int = 0
    truncated: bool = False


class EndpointTree(BaseModel):
    mode: str = "host"
    nodes: list[TreeNode] = PydanticField(default_factory=list)
    total_endpoints: int = 0
    total_nodes: int = 0
    truncated: bool = False
    error: QueryError | None = None


class CoverageRead(BaseModel):
    id: uuid.UUID
    source: str
    label: str
    tool: str | None = None
    status: str
    hosts_total: int = 0
    hosts_scanned: int | None = None
    hosts_dropped: list[str] = PydanticField(default_factory=list)
    urls_found: int | None = None
    urls_stored: int | None = None
    urls_probed: int | None = None
    pages_fetched: int | None = None
    depth_reached: int | None = None
    errors: int | None = None
    capped: bool = False
    cap_reason: str | None = None
    error: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = None


class EndpointSummary(BaseModel):
    total: int = 0
    probed: int = 0
    live: int = 0
    with_params: int = 0
    interesting: int = 0
    hosts: int = 0
    new: int = 0
    gone: int = 0
    previous_scan_id: uuid.UUID | None = None
    previous_scan_at: datetime | None = None
    by_class: dict[str, int] = PydanticField(default_factory=dict)
    by_source: dict[str, int] = PydanticField(default_factory=dict)


class GonePage(EndpointPage):
    """Endpoints the previous scan of this target recorded and this scan did not."""

    previous_scan_id: uuid.UUID | None = None
    previous_scan_at: datetime | None = None


class StructureFinding(BaseModel):
    """Something about the shape of the surface that is worth acting on."""

    kind: str
    label: str
    detail: str
    count: int
    query: str
    samples: list[str] = PydanticField(default_factory=list)


class PathSpread(BaseModel):
    path: str
    hosts: int
    endpoints: int
    query: str


class StructureLine(BaseModel):
    key: str
    label: str
    detail: str | None = None
    count: int
    hosts: int = 0
    query: str


class ScanStructure(BaseModel):
    endpoints: int = 0
    hosts: int = 0
    probed: int = 0
    directories: int = 0
    max_depth: int = 0
    with_params: int = 0
    headline: str | None = None
    findings: list[StructureFinding] = PydanticField(default_factory=list)
    shared_paths: list[PathSpread] = PydanticField(default_factory=list)
    interest: list[StructureLine] = PydanticField(default_factory=list)
    by_class: list[StructureLine] = PydanticField(default_factory=list)
    by_source: list[StructureLine] = PydanticField(default_factory=list)


class VerifyBranchRequest(BaseModel):
    host: str = PydanticField(max_length=500)
    dir_path: str | None = PydanticField(default=None, max_length=1500)
    limit: int = PydanticField(default=500, ge=1, le=2000)


class VerifyBranchResponse(BaseModel):
    queued: int = 0
    unverified: int = 0
    accepted: bool = False
