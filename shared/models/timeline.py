import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.definitions.timeline import (
    DEFAULT_TIMELINE_WINDOW,
    MAX_TIMELINE_SCANS,
    AddressFlag,
    AddressSort,
    PortFlag,
    RenderFlag,
    RenderSort,
    ServiceTimelineMode,
    TimelineFlag,
    TimelineSort,
)
from shared.models.asset_query import QueryError
from shared.models.scan_correlation import ServiceFilter
from shared.models.subdomain import SubdomainFilter, SubdomainRead


class TimelineFilter(SubdomainFilter):
    """The web assets filter plus the window and the flag the view narrows to."""

    window: int = Field(default=DEFAULT_TIMELINE_WINDOW, ge=2, le=MAX_TIMELINE_SCANS)
    flag: TimelineFlag | None = None
    sort: str = Field(default=TimelineSort.LAST_CHANGE.value, max_length=20)
    order: str = Field(default="desc", max_length=4)


class TimelineScan(BaseModel):
    """One column."""

    id: uuid.UUID
    started_at: datetime | None = None
    status: str
    observation: str


class TimelineCell(BaseModel):
    state: str
    status: int | None = None
    changed: list[str] = Field(default_factory=list)


class TimelineRow(BaseModel):
    host: SubdomainRead
    cells: list[TimelineCell] = Field(default_factory=list)
    state: str
    flags: list[str] = Field(default_factory=list)
    transitions: int = 0
    attribute_changes: int = 0
    first_seen_at: datetime | None = None
    last_change_scan_id: uuid.UUID | None = None


class TimelineSearchResult(BaseModel):
    scans: list[TimelineScan] = Field(default_factory=list)
    runs: int = 0
    items: list[TimelineRow] = Field(default_factory=list)
    total: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    error: QueryError | None = None


class RenderFilter(SubdomainFilter):
    """The web assets filter plus the window and the render flag the view narrows to."""

    window: int = Field(default=DEFAULT_TIMELINE_WINDOW, ge=2, le=MAX_TIMELINE_SCANS)
    flag: RenderFlag | None = None
    sort: str = Field(default=RenderSort.LAST_CHANGE.value, max_length=20)
    order: str = Field(default="desc", max_length=4)


class RenderCell(BaseModel):
    state: str
    path: str | None = None
    distance: int | None = None


class RenderRow(BaseModel):
    host: SubdomainRead
    cells: list[RenderCell] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    changes: int = 0
    first_capture_at: datetime | None = None
    last_change_scan_id: uuid.UUID | None = None


class RenderSearchResult(BaseModel):
    scans: list[TimelineScan] = Field(default_factory=list)
    runs: int = 0
    items: list[RenderRow] = Field(default_factory=list)
    total: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    error: QueryError | None = None


class ServiceTimelineFilter(ServiceFilter):
    """The services filter plus the window, the mode and the flag the view narrows to."""

    window: int = Field(default=DEFAULT_TIMELINE_WINDOW, ge=2, le=MAX_TIMELINE_SCANS)
    mode: ServiceTimelineMode = ServiceTimelineMode.ADDRESS
    flag: AddressFlag | PortFlag | None = None
    sort: str = Field(default=AddressSort.LAST_CHANGE.value, max_length=20)
    order: str = Field(default="desc", max_length=4)


class PortChange(BaseModel):
    """One port that opened or closed on an address in a run."""

    port: int
    protocol: str
    service_name: str | None = None
    product: str | None = None
    version: str | None = None
    first_on_address: bool = False
    first_on_target: bool = False
    open_since: datetime | None = None


class AddressCell(BaseModel):
    state: str
    opened: list[PortChange] = Field(default_factory=list)
    closed: list[PortChange] = Field(default_factory=list)
    software: list[PortChange] = Field(default_factory=list)


class LaneCell(BaseModel):
    state: str
    service_id: uuid.UUID | None = None
    software_changed: bool = False


class ServiceLane(BaseModel):
    port: int
    protocol: str
    service_name: str | None = None
    service_class: str | None = None
    product: str | None = None
    version: str | None = None
    open_now: bool = False
    cells: list[LaneCell] = Field(default_factory=list)
    first_seen_at: datetime | None = None
    opened_scan_id: uuid.UUID | None = None
    closed_scan_id: uuid.UUID | None = None
    events: int = 0
    software_changes: int = 0


class ServiceAddressRow(BaseModel):
    ip: str
    hosts: list[str] = Field(default_factory=list)
    host_count: int = 0
    asn_org: str | None = None
    country: str | None = None
    is_cdn: bool = False
    cells: list[AddressCell] = Field(default_factory=list)
    lanes: list[ServiceLane] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    open_now: int = 0
    changes: int = 0
    first_seen_at: datetime | None = None
    last_change_scan_id: uuid.UUID | None = None


class PortCell(BaseModel):
    state: str
    count: int = 0
    delta: int = 0
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    more: int = 0


class ServicePortRow(BaseModel):
    port: int
    protocol: str
    service_name: str | None = None
    product: str | None = None
    cells: list[PortCell] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    now: int = 0
    peak: int = 0
    first_seen_at: datetime | None = None
    last_change_scan_id: uuid.UUID | None = None


class ServiceTimelineResult(BaseModel):
    scans: list[TimelineScan] = Field(default_factory=list)
    runs: int = 0
    mode: ServiceTimelineMode = ServiceTimelineMode.ADDRESS
    addresses: list[ServiceAddressRow] = Field(default_factory=list)
    ports: list[ServicePortRow] = Field(default_factory=list)
    total: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    error: QueryError | None = None
