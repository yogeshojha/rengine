import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from shared.utils.datetime import utc_now


class TargetBgpSummary(SQLModel, table=True):
    __tablename__ = "target_bgp_summaries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    target_id: uuid.UUID = Field(foreign_key="targets.id", unique=True, index=True)

    # ASN targets
    prefix_count: int | None = Field(default=None)
    peer_count: int | None = Field(default=None)
    announced: bool | None = Field(default=None)

    # IP / IP_RANGE targets
    asn: int | None = Field(default=None)
    prefix: str | None = Field(default=None)
    holder: str | None = Field(default=None)

    queried_at: datetime = Field(default_factory=utc_now)


class BgpSummaryRead(BaseModel):
    prefix_count: int | None = None
    peer_count: int | None = None
    announced: bool | None = None
    asn: int | None = None
    prefix: str | None = None
    holder: str | None = None
    queried_at: datetime | None = None
