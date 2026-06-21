import uuid
from datetime import datetime

from sqlmodel import Field, Index, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now


class RIPEStatQueryLog(SQLModel, table=True):
    __tablename__ = "ripestat_query_log"
    __table_args__ = (
        UniqueConstraint(
            "lookup_type", "query_value", name="uq_ripestat_query_log_lookup"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    lookup_type: str = Field(index=True)
    query_value: str = Field(index=True)
    result_count: int = Field(default=0)
    queried_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RIPEStatAnnouncedPrefix(SQLModel, table=True):
    __tablename__ = "ripestat_announced_prefixes"
    __table_args__ = (
        Index("ix_ripestat_ap_asn", "asn"),
        Index("ix_ripestat_ap_prefix", "prefix"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asn: int
    prefix: str
    ip_version: int = Field(default=4)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    queried_at: datetime = Field(default_factory=utc_now)


class RIPEStatASNNeighbour(SQLModel, table=True):
    __tablename__ = "ripestat_asn_neighbours"
    __table_args__ = (
        Index("ix_ripestat_an_asn", "asn"),
        Index("ix_ripestat_an_neighbour", "neighbour_asn"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asn: int
    neighbour_asn: int
    relationship: str
    power: int = Field(default=0)
    queried_at: datetime = Field(default_factory=utc_now)


class RIPEStatASOverview(SQLModel, table=True):
    __tablename__ = "ripestat_as_overviews"
    __table_args__ = (
        UniqueConstraint("asn", name="uq_ripestat_as_overview_asn"),
        Index("ix_ripestat_aso_holder", "holder"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asn: int = Field(index=True)
    holder: str = Field(default="")
    rir: str | None = None
    announced: bool = Field(default=False)
    block_name: str | None = None
    block_resource: str | None = None
    queried_at: datetime = Field(default_factory=utc_now)


class RIPEStatNetworkInfo(SQLModel, table=True):
    __tablename__ = "ripestat_network_info"
    __table_args__ = (
        Index("ix_ripestat_ni_ip", "ip"),
        Index("ix_ripestat_ni_prefix", "prefix"),
        Index("ix_ripestat_ni_asn", "asn"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ip: str
    prefix: str = Field(default="")
    asn: int = Field(default=0)
    queried_at: datetime = Field(default_factory=utc_now)


class RIPEStatAbuseContact(SQLModel, table=True):
    __tablename__ = "ripestat_abuse_contacts"
    __table_args__ = (Index("ix_ripestat_ac_resource", "resource"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resource: str
    abuse_email: str
    rir: str | None = None
    queried_at: datetime = Field(default_factory=utc_now)


class RIPEStatPrefixOverview(SQLModel, table=True):
    __tablename__ = "ripestat_prefix_overviews"
    __table_args__ = (
        Index("ix_ripestat_po_prefix", "prefix"),
        Index("ix_ripestat_po_asn", "asn"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prefix: str
    asn: int
    holder: str = Field(default="")
    is_announced: bool = Field(default=True)
    queried_at: datetime = Field(default_factory=utc_now)


class RIPEStatRelatedPrefix(SQLModel, table=True):
    __tablename__ = "ripestat_related_prefixes"
    __table_args__ = (
        Index("ix_ripestat_rp_prefix", "prefix"),
        Index("ix_ripestat_rp_related", "related_prefix"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prefix: str
    related_prefix: str
    relationship: str
    origin_asn: int | None = None
    queried_at: datetime = Field(default_factory=utc_now)
