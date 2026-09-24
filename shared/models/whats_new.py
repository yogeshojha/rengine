from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shared.definitions.whats_new import NewTone


class NewItem(BaseModel):
    id: str
    kind: str
    at: datetime
    value: str
    detail: str | None = None
    tone: str = NewTone.NEW.value
    status: int | None = None
    title: str | None = None
    tech: list[str] = Field(default_factory=list)
    ips: list[str] = Field(default_factory=list)
    source: str | None = None
    source_label: str | None = None
    screenshot_path: str | None = None
    asset_type: str | None = None
    query: str | None = None
    target_id: uuid.UUID | None = None
    target_value: str | None = None
    target_type: str | None = None
    scan_id: uuid.UUID | None = None
    watch_id: uuid.UUID | None = None
    host_id: uuid.UUID | None = None
    scope_id: uuid.UUID | None = None
    platform: str | None = None
    handle: str | None = None
    program_name: str | None = None
    program_url: str | None = None
    importable: bool = False
    target_exists: bool | None = None
    scanned: bool | None = None
    muted: bool = False


class NewSection(BaseModel):
    kind: str
    total: int
    items: list[NewItem] = Field(default_factory=list)


class NewSubject(BaseModel):
    kind: str
    id: str | None = None
    label: str
    target_id: uuid.UUID | None = None
    target_value: str | None = None
    target_type: str | None = None
    platform: str | None = None
    handle: str | None = None
    watched: bool = False
    watch_id: uuid.UUID | None = None


class NewEvidence(BaseModel):
    kind: str
    label: str
    count: int
    severity: str | None = None
    kev: int = 0
    query: str


class NewGroup(BaseModel):
    id: str
    subject: NewSubject
    at: datetime
    counts: dict[str, int] = Field(default_factory=dict)
    sections: list[NewSection] = Field(default_factory=list)
    scan_id: uuid.UUID | None = None
    scan_started_at: datetime | None = None
    scan_status: str | None = None
    previous_scan_id: uuid.UUID | None = None
    severities: dict[str, int] = Field(default_factory=dict)
    completed_at: datetime | None = None
    evidence: list[NewEvidence] = Field(default_factory=list)
    more: int = 0


class NewDay(BaseModel):
    date: str
    counts: dict[str, int] = Field(default_factory=dict)


class NewFeed(BaseModel):
    since: datetime
    until: datetime | None = None
    basis: str
    marked_at: datetime | None = None
    window: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    facts: dict[str, dict[str, int]] = Field(default_factory=dict)
    daily: list[NewDay] = Field(default_factory=list)
    groups: list[NewGroup] = Field(default_factory=list)
    events: int = 0
    truncated: bool = False
    visual: int = 0


class VisualPair(BaseModel):
    id: str
    host: str
    at: datetime
    distance: int
    before_path: str
    after_path: str
    before_status: int | None = None
    after_status: int | None = None
    before_title: str | None = None
    after_title: str | None = None
    before_tech: list[str] = Field(default_factory=list)
    after_tech: list[str] = Field(default_factory=list)
    before_server: str | None = None
    after_server: str | None = None
    moved: list[str] = Field(default_factory=list)
    silent: bool = False
    target_id: uuid.UUID
    target_value: str
    target_type: str
    scan_id: uuid.UUID
    previous_scan_id: uuid.UUID
    query: str


class VisualFeed(BaseModel):
    since: datetime
    until: datetime | None = None
    basis: str
    window: str | None = None
    total: int = 0
    silent: int = 0
    pairs: list[VisualPair] = Field(default_factory=list)
    truncated: bool = False


class NewMark(BaseModel):
    marked_at: datetime


class NewUnseen(BaseModel):
    count: int
    since: datetime | None = None
