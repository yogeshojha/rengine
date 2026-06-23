import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TakeoverCandidate(BaseModel):
    name: str
    target_id: uuid.UUID
    cname: str
    provider: str
    last_seen: datetime


class TakeoverSignal(BaseModel):
    count: int
    items: list[TakeoverCandidate] = Field(default_factory=list)


class SpoofableDomain(BaseModel):
    target_id: uuid.UUID
    target_value: str
    reason: str


class SpoofableSignal(BaseModel):
    count: int
    items: list[SpoofableDomain] = Field(default_factory=list)


class StaleTarget(BaseModel):
    target_id: uuid.UUID
    target_value: str
    target_type: str
    last_scanned_at: datetime | None = None


class StaleSignal(BaseModel):
    never_scanned: int
    stale: int
    items: list[StaleTarget] = Field(default_factory=list)


class DashboardSignals(BaseModel):
    takeover: TakeoverSignal
    spoofable: SpoofableSignal
    stale: StaleSignal
