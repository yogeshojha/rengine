from datetime import datetime

from pydantic import BaseModel


class DatasetRead(BaseModel):
    kind: str
    label: str
    description: str
    rows_noun: str
    status: str
    status_label: str
    rows: int | None = None
    error: str | None = None
    last_synced_at: datetime | None = None
    last_attempt_at: datetime | None = None
    duration_ms: int | None = None
    auto_sync: bool = False


class DatasetSyncResult(BaseModel):
    queued: bool
    detail: str | None = None


class QueueRead(BaseModel):
    name: str
    label: str
    service: str
    workers: int


class QueueHealth(BaseModel):
    responded: bool
    queues: list[QueueRead]
