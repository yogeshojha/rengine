import uuid
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.definitions.scan_surface import SurfaceClass, SurfaceState
from shared.utils.datetime import utc_now


def _json_list() -> Field:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


def _json_dict() -> Field:
    return Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


class ScanSurfaceItem(SQLModel, table=True):
    """One thing a vulnerability scanner was handed, or deliberately not."""

    __tablename__ = "scan_surface_items"
    __table_args__ = (
        Index("ix_scan_surface_scan_class", "scan_id", "class"),
        Index("ix_scan_surface_scan_asset", "scan_id", "http_asset_id"),
        Index("ix_scan_surface_target_value", "target_id", "value"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    class_: str = Field(
        default=SurfaceClass.ROOT.value,
        max_length=16,
        sa_column_kwargs={"name": "class"},
    )
    value: str = Field(max_length=2000)
    host: str | None = Field(default=None, max_length=500)
    port: int | None = Field(default=None)
    scheme: str | None = Field(default=None, max_length=8)

    http_asset_id: uuid.UUID | None = Field(default=None)
    endpoint_id: uuid.UUID | None = Field(default=None)
    port_id: uuid.UUID | None = Field(default=None)
    subdomain_id: uuid.UUID | None = Field(default=None)

    cluster_id: uuid.UUID | None = Field(default=None, index=True)
    representative_id: uuid.UUID | None = Field(default=None, index=True)
    cluster_signals: list = _json_list()
    members: int = Field(default=1)

    drop_reason: str | None = Field(default=None, max_length=32)
    rank: float = Field(default=0.0)
    batch: int | None = Field(default=None)
    guarded: bool = Field(default=False)
    tags: list = _json_list()
    unmapped_tech: list = _json_list()

    tiers_planned: list = _json_list()
    tiers_done: dict = _json_dict()
    state: str = Field(default=SurfaceState.PLANNED.value, max_length=16)
    note: str | None = Field(default=None, max_length=500)

    created_at: datetime = Field(default_factory=utc_now)


class SurfaceItemRead(BaseModel):
    id: uuid.UUID
    class_: str = PydanticField(alias="class")
    value: str
    host: str | None = None
    port: int | None = None
    scheme: str | None = None
    http_asset_id: uuid.UUID | None = None
    cluster_id: uuid.UUID | None = None
    representative_id: uuid.UUID | None = None
    representative_value: str | None = None
    cluster_signals: list[str] = PydanticField(default_factory=list)
    members: int = 1
    drop_reason: str | None = None
    rank: float = 0.0
    batch: int | None = None
    guarded: bool = False
    tags: list[str] = PydanticField(default_factory=list)
    unmapped_tech: list[str] = PydanticField(default_factory=list)
    tiers_planned: list[str] = PydanticField(default_factory=list)
    tiers_done: dict[str, str] = PydanticField(default_factory=dict)
    state: str
    note: str | None = None

    model_config = {"populate_by_name": True}


class SurfaceTierCount(BaseModel):
    tier: str
    label: str
    scanned: int = 0
    partial: int = 0
    not_scanned: int = 0


class SurfaceSummary(BaseModel):
    """What the scanner was handed, per class, and how far each tier got."""

    planned: bool = False
    roots: int = 0
    origins: int = 0
    covered: int = 0
    dropped: dict[str, int] = PydanticField(default_factory=dict)
    names: int = 0
    services: int = 0
    requests: int = 0
    bases: int = 0
    tiers: list[SurfaceTierCount] = PydanticField(default_factory=list)
    unmapped_tech: list[str] = PydanticField(default_factory=list)


class AssetSurface(BaseModel):
    """What the vulnerability scan did with one web asset."""

    state: str
    representative_id: uuid.UUID | None = None
    representative_value: str | None = None
    cluster_signals: list[str] = PydanticField(default_factory=list)
    members: int = 1
    drop_reason: str | None = None
    tiers_planned: list[str] = PydanticField(default_factory=list)
    tiers_done: dict[str, str] = PydanticField(default_factory=dict)
    tags: list[str] = PydanticField(default_factory=list)
    note: str | None = None
