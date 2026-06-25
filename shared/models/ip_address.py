import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now


class IpAddress(SQLModel, table=True):
    __tablename__ = "ip_addresses"
    __table_args__ = (UniqueConstraint("scan_id", "ip", name="uq_ipaddress_scan_ip"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    ip: str = Field(max_length=45, index=True)
    version: int = Field(default=4)
    source: str = Field(max_length=30, index=True)
    ptr_hostnames: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    asn: int | None = Field(default=None, index=True)
    asn_org: str | None = Field(default=None, max_length=255)
    prefix: str | None = Field(default=None, max_length=64)
    country: str | None = Field(default=None, max_length=10)
    is_cdn: bool = Field(default=False, index=True)
    cdn_name: str | None = Field(default=None, max_length=100)
    is_alive: bool | None = Field(default=None)

    discovered_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)


class IpAddressRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    ip: str
    version: int
    source: str
    ptr_hostnames: list[str] = Field(default_factory=list)
    asn: int | None = None
    asn_org: str | None = None
    prefix: str | None = None
    country: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    is_alive: bool | None = None
    discovered_at: datetime


class IpAddressSummary(BaseModel):
    total: int
    alive: int
    cdn: int
    by_source: dict[str, int] = Field(default_factory=dict)


class TargetIpAddressRead(BaseModel):
    ip: str
    version: int
    source: str
    ptr_hostnames: list[str] = Field(default_factory=list)
    asn: int | None = None
    asn_org: str | None = None
    prefix: str | None = None
    country: str | None = None
    is_cdn: bool = False
    cdn_name: str | None = None
    is_alive: bool | None = None
    scan_count: int
    last_scan_id: uuid.UUID
    first_seen: datetime
    last_seen: datetime
