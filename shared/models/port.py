import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.definitions.ports import PortSource, PortState, ServiceClass
from shared.utils.datetime import utc_now


class Port(SQLModel, table=True):
    __tablename__ = "ports"
    __table_args__ = (
        UniqueConstraint(
            "scan_id", "ip", "number", "protocol", name="uq_port_scan_ip_num_proto"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    scan_id: uuid.UUID = Field(foreign_key="scans.id", index=True, ondelete="CASCADE")
    target_id: uuid.UUID = Field(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)

    ip: str = Field(max_length=45, index=True)
    number: int = Field(index=True)
    protocol: str = Field(default="tcp", max_length=8)
    state: str = Field(default=PortState.OPEN.value, max_length=16)
    service_name: str | None = Field(default=None, max_length=64, index=True)
    service_class: str = Field(
        default=ServiceClass.OTHER.value, max_length=16, index=True
    )
    source: str = Field(max_length=30)

    is_http: bool = Field(default=False, index=True)
    tls: bool = Field(default=False)
    product: str | None = Field(default=None, max_length=200)
    version: str | None = Field(default=None, max_length=100)
    banner: str | None = Field(default=None, max_length=1000)
    cpe: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))

    discovered_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)


class PortRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    target_id: uuid.UUID
    ip: str
    number: int
    protocol: str
    state: str
    service_name: str | None = None
    service_class: str = ServiceClass.OTHER.value
    source: str = PortSource.NAABU.value
    is_http: bool = False
    tls: bool = False
    product: str | None = None
    version: str | None = None
    banner: str | None = None
    cpe: list[str] = Field(default_factory=list)
    discovered_at: datetime


class PortSummary(BaseModel):
    total: int
    by_service: dict[str, int] = Field(default_factory=dict)
