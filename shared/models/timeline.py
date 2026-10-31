import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.definitions.timeline import (
    DEFAULT_TIMELINE_WINDOW,
    MAX_TIMELINE_SCANS,
    RenderFlag,
    RenderSort,
    TimelineFlag,
    TimelineSort,
)
from shared.models.asset_query import QueryError
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
    items: list[RenderRow] = Field(default_factory=list)
    total: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    error: QueryError | None = None
