import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import BigInteger, Column
from sqlmodel import JSON, Relationship, SQLModel
from sqlmodel import Field as SQLField

from shared.enums.dns import DnsRecordType
from shared.utils.datetime import utc_now


class DnsLookup(SQLModel, table=True):
    __tablename__ = "dns_lookups"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True, index=True)

    host: str = SQLField(max_length=500)
    status_code: str = SQLField(default="", max_length=20)
    cdn: bool = SQLField(default=False)
    cdn_name: str = SQLField(default="", max_length=100)

    parsed_data: dict = SQLField(default_factory=dict, sa_column=Column(JSON))

    queried_at: datetime = SQLField(default_factory=utc_now)
    created_at: datetime = SQLField(default_factory=utc_now)
    updated_at: datetime = SQLField(default_factory=utc_now)

    records: list["DnsRecord"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )


class DnsRecord(SQLModel, table=True):
    __tablename__ = "dns_records"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True, index=True)
    dns_lookup_id: uuid.UUID = SQLField(
        foreign_key="dns_lookups.id", index=True, ondelete="CASCADE"
    )
    target_id: uuid.UUID = SQLField(
        foreign_key="targets.id", index=True, ondelete="CASCADE"
    )

    record_type: DnsRecordType = SQLField(index=True)
    value: str = SQLField(max_length=2000, index=True)

    priority: int | None = SQLField(default=None)
    weight: int | None = SQLField(default=None)
    port: int | None = SQLField(default=None)

    soa_email: str | None = SQLField(default=None, max_length=500)
    soa_serial: int | None = SQLField(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    soa_refresh: int | None = SQLField(default=None)
    soa_retry: int | None = SQLField(default=None)
    soa_expire: int | None = SQLField(default=None)
    soa_minttl: int | None = SQLField(default=None)

    caa_tag: str | None = SQLField(default=None, max_length=100)
    caa_flag: int | None = SQLField(default=None)

    created_at: datetime = SQLField(default_factory=utc_now)


class DnsRecordRead(BaseModel):
    id: uuid.UUID
    record_type: DnsRecordType
    value: str
    priority: int | None = None
    weight: int | None = None
    port: int | None = None
    soa_email: str | None = None
    soa_serial: int | None = None
    caa_tag: str | None = None
    caa_flag: int | None = None


class DnsLookupSummary(BaseModel):
    id: uuid.UUID
    host: str
    status_code: str = ""
    cdn: bool = False
    cdn_name: str = ""
    queried_at: datetime
    record_counts: dict[str, int] = Field(default_factory=dict)


class DnsLookupRead(DnsLookupSummary):
    records: list[DnsRecordRead] = Field(default_factory=list)
