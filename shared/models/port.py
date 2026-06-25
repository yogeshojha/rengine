import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel, UniqueConstraint

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
    state: str = Field(default="open", max_length=16)
    service_name: str | None = Field(default=None, max_length=64)
    source: str = Field(max_length=30)

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
    source: str
    discovered_at: datetime


class PortSummary(BaseModel):
    total: int
    by_service: dict[str, int] = Field(default_factory=dict)
