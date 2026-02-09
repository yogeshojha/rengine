import uuid
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, UniqueConstraint

from shared.utils.datetime import utc_now


class ViewDNSCache(SQLModel, table=True):
    __tablename__ = "viewdns_cache"
    __table_args__ = (
        UniqueConstraint("lookup_type", "query_value", name="uq_viewdns_cache_lookup"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    lookup_type: str = Field(index=True)
    query_value: str = Field(index=True)
    result_count: int = Field(default=0)
    response_data: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, default={})
    )
    queried_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
