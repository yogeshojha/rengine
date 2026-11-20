import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Column, Index, PrimaryKeyConstraint, text
from sqlalchemy.types import JSON
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from shared.definitions.infostealer import (
    MAX_DOMAIN_LENGTH,
    MAX_HOST_LENGTH,
    MAX_PATH_LENGTH,
)
from shared.utils.datetime import utc_now


class TargetInfostealer(SQLModel, table=True):
    __tablename__ = "target_infostealers"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    target_id: uuid.UUID = SQLField(
        foreign_key="targets.id", unique=True, index=True, ondelete="CASCADE"
    )
    domain: str = SQLField(max_length=MAX_DOMAIN_LENGTH)
    checked_at: datetime = SQLField(default_factory=utc_now)

    total: int = SQLField(default=0)
    employees: int = SQLField(default=0)
    users: int = SQLField(default=0)
    third_parties: int = SQLField(default=0)
    total_urls: int = SQLField(default=0)
    last_employee_at: datetime | None = SQLField(default=None)
    last_user_at: datetime | None = SQLField(default=None)
    employees_peak: int = SQLField(default=0)
    users_peak: int = SQLField(default=0)

    families: list = SQLField(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    passwords: dict = SQLField(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    applications: list = SQLField(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    services: list = SQLField(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )


class InfostealerLogin(SQLModel, table=True):
    __tablename__ = "infostealer_logins"
    __table_args__ = (Index("ix_infostealer_logins_target_host", "target_id", "host"),)

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    target_id: uuid.UUID = SQLField(foreign_key="targets.id", ondelete="CASCADE")
    audience: str = SQLField(max_length=16)
    host: str = SQLField(max_length=MAX_HOST_LENGTH)
    scheme: str | None = SQLField(default=None, max_length=16)
    port: int | None = SQLField(default=None)
    path: str | None = SQLField(default=None, max_length=MAX_PATH_LENGTH)
    credentials: int = SQLField(default=0)


class InfostealerSighting(SQLModel, table=True):
    """The first lookup that listed a host for an audience, and its highest count."""

    __tablename__ = "infostealer_sightings"
    __table_args__ = (PrimaryKeyConstraint("target_id", "audience", "host"),)

    target_id: uuid.UUID = SQLField(foreign_key="targets.id", ondelete="CASCADE")
    audience: str = SQLField(max_length=16)
    host: str = SQLField(max_length=MAX_HOST_LENGTH)
    first_seen: datetime = SQLField(default_factory=utc_now)
    credentials_peak: int = SQLField(default=0)


class InfostealerChange(SQLModel, table=True):
    """What one lookup added to a target's report."""

    __tablename__ = "infostealer_changes"
    __table_args__ = (
        Index("ix_infostealer_changes_target_checked", "target_id", "checked_at"),
        Index(
            "ix_infostealer_changes_pending",
            "checked_at",
            postgresql_where=text("evaluated_at IS NULL"),
        ),
    )

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    target_id: uuid.UUID = SQLField(foreign_key="targets.id", ondelete="CASCADE")
    checked_at: datetime = SQLField(default_factory=utc_now)
    previous_checked_at: datetime | None = SQLField(default=None)
    employees_from: int = SQLField(default=0)
    employees_to: int = SQLField(default=0)
    users_from: int = SQLField(default=0)
    users_to: int = SQLField(default=0)
    hosts: list = SQLField(default_factory=list, sa_column=Column(JSON, nullable=False))
    evaluated_at: datetime | None = SQLField(default=None)


class ChangeHost(BaseModel):
    audience: str
    host: str
    credentials_from: int = 0
    credentials_to: int = 0
    new: bool = False


class InfostealerChangeRead(BaseModel):
    id: uuid.UUID
    checked_at: datetime
    previous_checked_at: datetime | None = None
    employees_from: int = 0
    employees_to: int = 0
    users_from: int = 0
    users_to: int = 0
    hosts: list[ChangeHost] = Field(default_factory=list)


class InfostealerWatcher(BaseModel):
    id: uuid.UUID
    name: str


class NamedCountRead(BaseModel):
    name: str
    count: int | None = None


class InfostealerSummary(BaseModel):
    domain: str
    checked_at: datetime
    total: int = 0
    employees: int = 0
    users: int = 0
    third_parties: int = 0
    host_count: int = 0


class InfostealerPath(BaseModel):
    audience: str
    scheme: str | None = None
    port: int | None = None
    path: str | None = None
    credentials: int = 0


class InfostealerHost(BaseModel):
    host: str
    employee_credentials: int = 0
    user_credentials: int = 0
    standing: str
    first_seen: datetime | None = None
    paths: list[InfostealerPath] = Field(default_factory=list)


class TargetInfostealerRead(InfostealerSummary):
    total_urls: int = 0
    last_employee_at: datetime | None = None
    last_user_at: datetime | None = None
    scan_id: uuid.UUID | None = None
    in_scan: int = 0
    query: str
    hosts: list[InfostealerHost] = Field(default_factory=list)
    families: list[NamedCountRead] = Field(default_factory=list)
    passwords: dict[str, dict[str, int]] = Field(default_factory=dict)
    applications: list[NamedCountRead] = Field(default_factory=list)
    services: list[NamedCountRead] = Field(default_factory=list)
    changes: list[InfostealerChangeRead] = Field(default_factory=list)
    watchers: list[InfostealerWatcher] = Field(default_factory=list)
