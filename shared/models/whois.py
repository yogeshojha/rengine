import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from shared.enums.whois import WhoisLookupType
from shared.utils.datetime import utc_now


class WhoisRecord(SQLModel, table=True):
    __tablename__ = "whois_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    query_value: str = Field(max_length=500, index=True, unique=True)
    lookup_type: WhoisLookupType
    queried_at: datetime = Field(
        default_factory=utc_now,
        description="When RDAP was last queried for this record",
    )

    handle: str = Field(default="", max_length=200)
    name: str = Field(default="", max_length=500, index=True)
    whois_server: str = Field(default="", max_length=200)
    object_class: str = Field(default="", max_length=100)
    rir: str = Field(default="", max_length=50)
    description: str = Field(default="", sa_type=Text)

    registration_date: datetime | None = None
    last_changed_date: datetime | None = None
    expiration_date: datetime | None = None

    registrant_name: str = Field(default="", max_length=500, index=True)
    registrant_email: str = Field(default="", max_length=500, index=True)
    registrar_name: str = Field(default="", max_length=500, index=True)
    abuse_email: str = Field(default="", max_length=500)

    nameservers: list | None = Field(default=None, sa_type=JSONB)
    domain_status: list | None = Field(default=None, sa_type=JSONB)
    dnssec: bool | None = None

    country: str = Field(default="", max_length=10, index=True)
    ip_version: int | None = None
    assignment_type: str = Field(default="", max_length=100)
    network_cidr: str = Field(default="", max_length=100, index=True)

    asn_range_start: int | None = None
    asn_range_end: int | None = None

    parsed_data: dict | None = Field(default=None, sa_type=JSONB)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WhoisNameserver(SQLModel, table=True):
    __tablename__ = "whois_nameservers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    whois_record_id: uuid.UUID = Field(
        foreign_key="whois_records.id",
        index=True,
        ondelete="CASCADE",
    )
    nameserver: str = Field(max_length=500, index=True)


class WhoisRecordRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    query_value: str
    lookup_type: str
    queried_at: datetime

    handle: str
    name: str
    whois_server: str
    object_class: str = Field(default="")
    rir: str
    description: str

    registration_date: datetime | None
    last_changed_date: datetime | None
    expiration_date: datetime | None

    registrant_name: str
    registrant_email: str
    registrar_name: str
    abuse_email: str

    nameservers: list | None
    domain_status: list | None
    dnssec: bool | None

    country: str
    ip_version: int | None
    assignment_type: str
    network_cidr: str

    asn_range_start: int | None
    asn_range_end: int | None

    parsed_data: dict | None

    created_at: datetime
    updated_at: datetime


class WhoisRecordSummary(BaseModel):
    id: uuid.UUID
    query_value: str
    lookup_type: str
    name: str
    registrant_name: str
    registrar_name: str
    country: str
    network_cidr: str
    registration_date: datetime | None
    expiration_date: datetime | None
    queried_at: datetime


class WhoisCorrelationResult(BaseModel):
    correlation_type: str
    correlation_value: str
    records: list[WhoisRecordSummary]
    count: int
